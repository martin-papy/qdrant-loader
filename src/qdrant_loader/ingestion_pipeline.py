from typing import List, Optional
import structlog
from .config import SourcesConfig, get_settings
from .connectors.public_docs import PublicDocsConnector
from .core.document import Document
from .embedding_service import EmbeddingService
from .qdrant_manager import QdrantManager
from datetime import datetime

logger = structlog.get_logger()

class IngestionPipeline:
    """Pipeline for processing and ingesting documents from various sources."""
    
    def __init__(self):
        """Initialize the ingestion pipeline with required services."""
        self.settings = get_settings()
        if not self.settings:
            raise ValueError("Settings not available. Please check your environment variables.")
            
        self.embedding_service = EmbeddingService(self.settings)
        self.qdrant_manager = QdrantManager(self.settings)
        
    def _process_public_docs(self, sources: dict) -> List[Document]:
        """Process documents from public documentation sources."""
        documents = []
        
        for source_name, source_config in sources.items():
            try:
                logger.info("Processing public docs source", source=source_name)
                connector = PublicDocsConnector(source_config)
                contents = connector.get_documentation()
                
                for content in contents:
                    document = Document(
                        content=content,
                        source=source_name,
                        source_type="public_docs",
                        url=source_config.base_url,
                        last_updated=datetime.now(),
                        metadata={
                            "version": source_config.version,
                            "content_type": source_config.content_type
                        }
                    )
                    documents.append(document)
                    
            except Exception as e:
                logger.error("Failed to process public docs source", 
                           source=source_name, 
                           error=str(e))
                continue
                
        return documents
        
    def process_documents(self, config: SourcesConfig) -> None:
        """Process and ingest documents from all configured sources."""
        try:
            documents = []
            
            # Process public documentation sources
            if config.public_docs:
                public_docs = self._process_public_docs(config.public_docs)
                documents.extend(public_docs)
                
            if not documents:
                logger.warning("No documents were processed")
                return
                
            # Generate embeddings for all documents
            logger.info("Generating embeddings", document_count=len(documents))
            embeddings = self.embedding_service.generate_embeddings(
                [doc.content for doc in documents]
            )
            
            # Prepare points for qDrant
            points = []
            for doc, embedding in zip(documents, embeddings):
                points.append({
                    "id": doc.metadata.get("url", doc.source),
                    "vector": embedding,
                    "payload": doc.metadata
                })
                
            # Upload to qDrant
            logger.info("Uploading documents to qDrant", point_count=len(points))
            self.qdrant_manager.upload_points(points)
            
        except Exception as e:
            logger.error("Failed to process documents", error=str(e))
            raise 