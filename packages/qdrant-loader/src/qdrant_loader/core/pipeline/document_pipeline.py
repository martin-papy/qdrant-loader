"""Document processing pipeline that coordinates chunking, embedding, and upserting."""

import asyncio
import time
from dataclasses import dataclass

import qdrant_loader_core.graph.registry as _registry  # noqa: F401
from qdrant_loader_core.graph import get_graph_store
from qdrant_loader_core.graph.extractor.base_extractor import EntityExtractor

from qdrant_loader.config import get_settings
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

from .workers import ChunkingWorker, EmbeddingWorker, UpsertWorker
from .workers.upsert_worker import PipelineResult

logger = LoggingConfig.get_logger(__name__)


@dataclass
class BatchResult:
    """Result of processing a bounded batch of documents."""

    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    successfully_processed_documents: set[str] | None = None
    failed_document_ids: set[str] | None = None
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.successfully_processed_documents is None:
            self.successfully_processed_documents = set()
        if self.failed_document_ids is None:
            self.failed_document_ids = set()
        if self.errors is None:
            self.errors = []


class DocumentPipeline:
    """Handles the chunking -> embedding -> upsert pipeline."""

    def __init__(
        self,
        chunking_worker: ChunkingWorker,
        embedding_worker: EmbeddingWorker,
        upsert_worker: UpsertWorker,
    ):
        self.chunking_worker = chunking_worker
        self.embedding_worker = embedding_worker
        self.upsert_worker = upsert_worker

    async def _process_graph(
        self,
        documents: list[Document],
        current_project_id: str | None = None,
    ) -> None:
        # Optional: Graph extraction & upsert (graph is optional; failures must not fail ingestion)
        try:
            try:
                # Use the global settings initialized via initialize_config()/initialize_config_with_workspace
                settings = get_settings()
                graph_cfg = getattr(settings.global_config, "graph", None)
                graph_enabled = (
                    bool(getattr(graph_cfg, "enabled", None))
                    if graph_cfg is not None
                    else False
                )
            except Exception:
                # If settings aren't initialized or any error occurs, treat graph as disabled
                graph_enabled = False

            if graph_enabled:
                # Ensure extractor registry is imported (registers available extractors)
                logger.info("🔄 Starting graph extraction phase for batch...")

                # Use dict to deduplicate nodes and edges by ID
                nodes_dict: dict[str, any] = {}  # node_id -> node
                edges_dict: dict[str, any] = {}  # (source, target, edge_type) -> edge

                for doc in documents:
                    try:
                        extractor = EntityExtractor.for_source(doc.source_type)

                        metadata = getattr(doc, "metadata", {}) or {}
                        raw = {
                            **metadata,
                            "id": metadata.get("id", getattr(doc, "id", None)),
                            "content": getattr(doc, "content", None),
                            "path": getattr(doc, "path", None)
                            or metadata.get("path")
                            or getattr(doc, "source", None)
                            or getattr(doc, "title", None),
                            "file_name": metadata.get("file_name"),
                            "source_type": doc.source_type,
                        }
                        subgraph = extractor.extract(raw)

                        # Deduplicate nodes by ID
                        if getattr(subgraph, "nodes", None):
                            for node in subgraph.nodes:
                                nodes_dict[node.id] = node

                        # Deduplicate edges by (source, target, edge_type)
                        if getattr(subgraph, "edges", None):
                            for edge in subgraph.edges:
                                edge_key = (edge.source, edge.target, edge.edge_type)
                                edges_dict[edge_key] = edge
                    except Exception as e:
                        logger.error(
                            "⚠️ Graph extraction failed for document %s: %s",
                            getattr(doc, "id", "<unknown>"),
                            e,
                            exc_info=True,
                        )

                # Convert deduplicated dicts back to lists
                nodes_batch = list(nodes_dict.values())
                edges_batch = list(edges_dict.values())

                # Ensure project context is attached to nodes/edges so
                # downstream graph store implementations can filter by project.
                if current_project_id:
                    for n in nodes_batch:
                        # prefer explicit attribute if present, else store in properties
                        try:
                            n.project = current_project_id
                        except Exception:
                            pass
                        n.properties = n.properties or {}
                        n.properties.setdefault("project", current_project_id)

                    for e in edges_batch:
                        try:
                            e.project = current_project_id
                        except Exception:
                            pass
                        e.properties = e.properties or {}
                        e.properties.setdefault("project", current_project_id)

                if nodes_batch or edges_batch:
                    try:
                        graph_store = await get_graph_store()
                        if nodes_batch:
                            await graph_store.upsert_nodes_batch(nodes_batch)
                        if edges_batch:
                            await graph_store.upsert_edges_batch(edges_batch)
                        logger.info("🔄 Add graph store successfully...")
                    except Exception as e:
                        logger.error(
                            "⚠️ Graph upsert failed (non-fatal): %s",
                            e,
                            exc_info=True,
                        )
                logger.info(
                    "Graph batch size: nodes=%s, edges=%s",
                    len(nodes_batch),
                    len(edges_batch),
                )
                logger.debug("Graph node ids: %s", [node.id for node in nodes_batch])
                logger.debug(
                    "Graph edges: %s",
                    [
                        (edge.source, edge.edge_type, edge.target)
                        for edge in edges_batch
                    ],
                )
        except Exception:
            logger.exception("Unexpected error during optional graph processing")

    async def process_batch(
        self,
        batch: list[Document],
        current_project_id: str | None = None,
    ) -> BatchResult:
        """Process a bounded batch of documents through the pipeline.

        Args:
            batch: List of documents to process (bounded size, typically 256)
            current_project_id: Optional project id context for graph extraction/upsert.

        Returns:
            BatchResult with processing statistics.
        """
        logger.info(f"⚙️ Processing batch of {len(batch)} documents through pipeline")
        start_time = time.time()

        try:
            logger.debug("🔄 Starting chunking phase for batch...")
            chunking_start = time.time()
            chunks_iter = self.chunking_worker.process_documents(batch)

            logger.debug("🔄 Chunking completed, transitioning to embedding phase...")
            chunking_duration = time.time() - chunking_start
            logger.debug(f"⏱️ Chunking phase took {chunking_duration:.2f} seconds")

            embedding_start = time.time()
            embedded_chunks_iter = self.embedding_worker.process_chunks(chunks_iter)

            logger.debug("🔄 Embedding phase ready, starting upsert phase...")

            try:
                pipeline_result = await asyncio.wait_for(
                    self.upsert_worker.process_embedded_chunks(embedded_chunks_iter),
                    timeout=600.0,  # 10 minute timeout per batch
                )
            except TimeoutError:
                logger.error("❌ Batch processing timed out after 10 minutes")
                return BatchResult(
                    failure_count=len(batch),
                    errors=["Batch processing timed out after 10 minutes"],
                )

            total_duration = time.time() - start_time
            embedding_duration = time.time() - embedding_start

            logger.debug(
                f"⏱️ Embedding + Upsert phase took {embedding_duration:.2f} seconds"
            )
            logger.info(
                f"✅ Batch processing completed: {pipeline_result.success_count} chunks, "
                f"{pipeline_result.error_count} errors in {total_duration:.2f}s"
            )

            # add node and edge
            await self._process_graph(batch, current_project_id)

            return BatchResult(
                success_count=pipeline_result.success_count,
                failure_count=pipeline_result.error_count,
                skipped_count=0,
                successfully_processed_documents=pipeline_result.successfully_processed_documents,
                failed_document_ids=pipeline_result.failed_document_ids,
                errors=pipeline_result.errors,
            )

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"❌ Batch processing failed after {total_duration:.2f} seconds: {e}",
                exc_info=True,
            )
            return BatchResult(
                failure_count=len(batch),
                errors=[f"Batch processing failed: {e}"],
            )

    async def process_documents(
        self,
        documents: list[Document],
        current_project_id: str | None = None,
    ) -> PipelineResult:
        """Process documents through the pipeline.

        Args:
            documents: List of documents to process
            current_project_id: Optional project id context for graph extraction/upsert.

        Returns:
            PipelineResult with processing statistics
        """
        logger.info(f"⚙️ Processing {len(documents)} documents through pipeline")
        start_time = time.time()

        try:
            logger.info("🔄 Starting chunking phase...")
            chunking_start = time.time()
            chunks_iter = self.chunking_worker.process_documents(documents)

            logger.info("🔄 Chunking completed, transitioning to embedding phase...")
            chunking_duration = time.time() - chunking_start
            logger.info(f"⏱️ Chunking phase took {chunking_duration:.2f} seconds")

            embedding_start = time.time()
            embedded_chunks_iter = self.embedding_worker.process_chunks(chunks_iter)

            logger.info("🔄 Embedding phase ready, starting upsert phase...")

            try:
                result = await asyncio.wait_for(
                    self.upsert_worker.process_embedded_chunks(embedded_chunks_iter),
                    timeout=3600.0,  # 1 hour timeout for the entire pipeline
                )
            except TimeoutError:
                logger.error("❌ Pipeline timed out after 1 hour")
                result = PipelineResult()
                result.error_count = len(documents)
                result.errors = ["Pipeline timed out after 1 hour"]
                return result

            total_duration = time.time() - start_time
            embedding_duration = time.time() - embedding_start

            logger.info(
                f"⏱️ Embedding + Upsert phase took {embedding_duration:.2f} seconds"
            )
            logger.info(f"⏱️ Total pipeline duration: {total_duration:.2f} seconds")
            logger.info(
                f"✅ Pipeline completed: {result.success_count} chunks processed, "
                f"{result.error_count} errors"
            )

            await self._process_graph(documents, current_project_id)

            return result

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"❌ Document pipeline failed after {total_duration:.2f} seconds: {e}",
                exc_info=True,
            )
            result = PipelineResult()
            result.error_count = len(documents)
            result.errors = [f"Pipeline failed: {e}"]
            return result
