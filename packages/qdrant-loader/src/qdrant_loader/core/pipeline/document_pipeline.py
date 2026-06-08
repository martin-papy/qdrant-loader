"""Document processing pipeline that coordinates chunking, embedding, and upserting."""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

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
        """
        Graph write hook (optional):
        - Extract entities + relations from documents
        - Build nodes/edges
        - Deduplicate
        - Batch upsert into GraphStore
        - Must NOT affect ingestion if fails
        """

        # ---------------------------
        # 1. Load config safely
        # ---------------------------
        try:
            settings = get_settings()
            graph_cfg = getattr(settings.global_config, "graph", None)
            graph_enabled = (
                bool(getattr(graph_cfg, "enabled", False)) if graph_cfg else False
            )
        except Exception:
            logger.warning("Graph config not available → graph disabled")
            return

        if not graph_enabled:
            return

        logger.info("🔄 Graph extraction started (batch size=%s)", len(documents))

        # ---------------------------
        # 2. Prepare dedup storage
        # ---------------------------
        nodes_dict: dict[str, Any] = {}
        edges_dict: dict[tuple[str, str, str], Any] = {}

        # Optional: group by source_type for efficiency
        grouped_docs: dict[str, list[Document]] = defaultdict(list)
        for doc in documents:
            grouped_docs[doc.source_type].append(doc)

        # ---------------------------
        # 3. Extract graph per source_type
        # ---------------------------
        for source_type, docs in grouped_docs.items():
            try:
                extractor = EntityExtractor.for_source(source_type)
                if not extractor:
                    logger.warning("No extractor found for source_type=%s", source_type)
                    continue

                for doc in docs:
                    try:
                        subgraph = await extractor.extract(doc)

                        if getattr(subgraph, "nodes", None):
                            for node in subgraph.nodes:
                                nodes_dict[node.id] = node

                        if getattr(subgraph, "edges", None):
                            for edge in subgraph.edges:
                                edge_key = (edge.source, edge.target, edge.edge_type)
                                edges_dict[edge_key] = edge

                    except Exception as e:
                        logger.error(
                            "⚠️ Graph extract failed doc_id=%s error=%s",
                            getattr(doc, "id", "<unknown>"),
                            e,
                            exc_info=True,
                        )

            except Exception as e:
                logger.error(
                    "⚠️ Extractor failed for source_type=%s error=%s",
                    source_type,
                    e,
                    exc_info=True,
                )

        # ---------------------------
        # 4. Build batches
        # ---------------------------
        nodes_batch = list(nodes_dict.values())
        edges_batch = list(edges_dict.values())

        # ---------------------------
        # 5. Attach project context
        # ---------------------------
        if current_project_id:
            for node in nodes_batch:
                if not hasattr(node, "properties") or node.properties is None:
                    node.properties = {}
                node.properties["project"] = current_project_id

            for edge in edges_batch:
                if not hasattr(edge, "properties") or edge.properties is None:
                    edge.properties = {}
                edge.properties["project"] = current_project_id

        # ---------------------------
        # 6. Batch upsert
        # ---------------------------
        if not nodes_batch and not edges_batch:
            logger.info("Graph extraction result is empty → skip upsert")
            return

        try:
            graph_store = await get_graph_store()

            if nodes_batch:
                await graph_store.upsert_nodes_batch(nodes_batch)

            if edges_batch:
                await graph_store.upsert_edges_batch(edges_batch)

            logger.info(
                "✅ Graph upsert success | nodes=%s edges=%s",
                len(nodes_batch),
                len(edges_batch),
            )

        except Exception as e:
            logger.error(
                "⚠️ Graph upsert failed (non-fatal): %s",
                e,
                exc_info=True,
            )

    async def process_batch(
        self, batch: list[Document], current_project_id: str | None = None
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

    async def process_documents(self, documents: list[Document]) -> PipelineResult:
        """Process documents through the pipeline.

        Args:
            documents: List of documents to process

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
