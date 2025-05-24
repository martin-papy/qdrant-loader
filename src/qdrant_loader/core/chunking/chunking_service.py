"""Service for chunking documents."""

from typing import Type
from pathlib import Path

from qdrant_loader.config import GlobalConfig, Settings
from qdrant_loader.core.chunking.strategy import (
    BaseChunkingStrategy,
    DefaultChunkingStrategy,
    MarkdownChunkingStrategy,
    HTMLChunkingStrategy,
    CodeChunkingStrategy,
    JSONChunkingStrategy,
)
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.core.monitoring.ingestion_metrics import IngestionMonitor


class ChunkingService:
    """Service for chunking documents into smaller pieces."""

    def __new__(cls, config: GlobalConfig, settings: Settings):
        """Create a new instance of ChunkingService.

        Args:
            config: Global configuration
            settings: Application settings
        """
        instance = super().__new__(cls)
        instance.__init__(config, settings)
        return instance

    def __init__(self, config: GlobalConfig, settings: Settings):
        """Initialize the chunking service.

        Args:
            config: Global configuration
            settings: Application settings
        """
        self.config = config
        self.settings = settings
        self.validate_config()
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize metrics directory
        metrics_dir = Path.cwd() / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        self.monitor = IngestionMonitor(str(metrics_dir.absolute()))

        # Initialize strategies
        self.strategies: dict[str, Type[BaseChunkingStrategy]] = {
            "md": MarkdownChunkingStrategy,
            "html": HTMLChunkingStrategy,
            # JSON files
            "json": JSONChunkingStrategy,
            # Programming languages
            "py": CodeChunkingStrategy,
            "java": CodeChunkingStrategy,
            "js": CodeChunkingStrategy,
            "ts": CodeChunkingStrategy,
            "go": CodeChunkingStrategy,
            "rs": CodeChunkingStrategy,
            "cpp": CodeChunkingStrategy,
            "c": CodeChunkingStrategy,
            "cs": CodeChunkingStrategy,
            "php": CodeChunkingStrategy,
            "rb": CodeChunkingStrategy,
            "kt": CodeChunkingStrategy,
            "swift": CodeChunkingStrategy,
            "scala": CodeChunkingStrategy,
            # Add more strategies here as needed
        }

        # Default strategy for unknown file types
        self.default_strategy = DefaultChunkingStrategy(
            settings=self.settings,
            chunk_size=config.chunking.chunk_size,
            chunk_overlap=config.chunking.chunk_overlap,
        )

    def validate_config(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If chunk size or overlap parameters are invalid.
        """
        if self.config.chunking.chunk_size <= 0:
            raise ValueError("Chunk size must be greater than 0")
        if self.config.chunking.chunk_overlap < 0:
            raise ValueError("Chunk overlap must be non-negative")
        if self.config.chunking.chunk_overlap >= self.config.chunking.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")

    def _get_strategy(self, document: Document) -> BaseChunkingStrategy:
        """Get the appropriate chunking strategy for a document.

        Args:
            document: The document to chunk

        Returns:
            The appropriate chunking strategy for the document type
        """
        # Get file extension from the document content type
        file_type = document.content_type.lower()

        self.logger.debug(
            "Selecting chunking strategy",
            file_type=file_type,
            available_strategies=list(self.strategies.keys()),
            document_id=document.id,
            document_source=document.source,
            document_title=document.title,
        )

        # Get strategy class for file type
        strategy_class = self.strategies.get(file_type)

        if strategy_class:
            self.logger.info(
                "Using specific strategy for file type",
                file_type=file_type,
                strategy=strategy_class.__name__,
                document_id=document.id,
                document_title=document.title,
            )
            return strategy_class(self.settings)

        self.logger.warning(
            "No specific strategy found for file type, using default strategy",
            file_type=file_type,
            document_id=document.id,
            document_title=document.title,
        )
        return self.default_strategy

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a document into smaller pieces.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.debug(
            "Starting document chunking",
            extra={
                "doc_id": document.id,
                "source": document.source,
                "source_type": document.source_type,
                "content_size": len(document.content),
                "content_type": document.content_type,
            },
        )

        if not document.content:
            # Return a single empty chunk if document has no content
            empty_doc = document.model_copy()
            empty_doc.metadata.update({"chunk_index": 0, "total_chunks": 1})
            self.logger.debug(
                "Empty document, returning single empty chunk",
                extra={"doc_id": document.id, "chunk_id": empty_doc.id},
            )
            return [empty_doc]

        # Get the appropriate strategy for the document type
        strategy = self._get_strategy(document)
        self.logger.debug(
            "Selected chunking strategy",
            extra={
                "doc_id": document.id,
                "strategy": strategy.__class__.__name__,
                "content_type": document.content_type,
            },
        )

        try:
            # Chunk the document using the selected strategy
            chunked_docs = strategy.chunk_document(document)
            self.logger.debug(
                "Document chunking completed",
                extra={
                    "doc_id": document.id,
                    "chunk_count": len(chunked_docs),
                    "avg_chunk_size": (
                        sum(len(d.content) for d in chunked_docs) / len(chunked_docs)
                        if chunked_docs
                        else 0
                    ),
                },
            )
            return chunked_docs
        except Exception as e:
            self.logger.error(
                f"Error chunking document {document.id}: {str(e)}",
                extra={
                    "doc_id": document.id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "strategy": strategy.__class__.__name__,
                },
            )
            raise
