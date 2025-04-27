"""Service for chunking documents."""

from typing import Type

from qdrant_loader.config import GlobalConfig, Settings
from qdrant_loader.core.chunking.strategy import (
    BaseChunkingStrategy,
    DefaultChunkingStrategy,
    MarkdownChunkingStrategy,
)
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.core.monitoring.performance_monitor import PerformanceMonitor


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
        self.monitor = PerformanceMonitor.get_monitor()
        
        # Initialize strategies
        self.strategies: dict[str, Type[BaseChunkingStrategy]] = {
            "md": MarkdownChunkingStrategy,
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
        file_type = document.content_type.lower().lstrip(".")
        
        # Get strategy class for file type
        strategy_class = self.strategies.get(file_type)
        
        if strategy_class:
            self.logger.debug(
                "Using specific strategy for file type",
                file_type=file_type,
                strategy=strategy_class.__name__,
            )
            return strategy_class(self.settings)
        
        self.logger.debug(
            "Using default strategy for file type",
            file_type=file_type,
        )
        return self.default_strategy

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a document into smaller pieces.

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents
        """
        if not document.content:
            # Return a single empty chunk if document has no content
            empty_doc = document.model_copy()
            empty_doc.metadata.update({"chunk_index": 0, "total_chunks": 1})
            return [empty_doc]

        try:
            # Update document metrics
            self.logger.debug(f"Updating document metrics for document {document.id}")
            self.monitor.storage.document_metrics['total_documents'] += 1
            self.monitor.storage.document_metrics['documents_by_source'][document.source] = self.monitor.storage.document_metrics['documents_by_source'].get(document.source, 0) + 1
            self.monitor.storage.document_metrics['documents_by_type'][document.source_type] = self.monitor.storage.document_metrics['documents_by_type'].get(document.source_type, 0) + 1
            self.monitor.storage.document_metrics['document_sizes'].append(len(document.content))
            self.logger.debug(f"Document metrics updated: total_documents={self.monitor.storage.document_metrics['total_documents']}, source={document.source}, type={document.source_type}")
            
            # Get appropriate strategy for document type
            strategy = self._get_strategy(document)
            
            # Chunk the document using the selected strategy
            chunked_docs = strategy.chunk_document(document)
            
            # Update chunk metrics
            self.logger.debug(f"Updating chunk metrics for document {document.id}")
            self.monitor.storage.chunk_metrics['total_chunks'] += len(chunked_docs)
            self.monitor.storage.chunk_metrics['chunks_per_document'][document.id] = len(chunked_docs)
            self.monitor.storage.chunk_metrics['chunk_sizes'].extend([len(doc.content) for doc in chunked_docs])
            strategy_name = strategy.__class__.__name__
            self.monitor.storage.chunk_metrics['chunk_strategies'][strategy_name] = self.monitor.storage.chunk_metrics['chunk_strategies'].get(strategy_name, 0) + 1
            self.logger.debug(f"Chunk metrics updated: total_chunks={self.monitor.storage.chunk_metrics['total_chunks']}, chunks_per_document={len(chunked_docs)}, strategy={strategy_name}")
            
            return chunked_docs
        except Exception as e:
            self.logger.error(f"Error updating metrics for document {document.id}: {str(e)}", exc_info=True)
            # Re-raise the exception to maintain the original error handling
            raise
