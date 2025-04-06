from typing import List, Optional
import structlog
from .config import SourcesConfig, get_settings, get_global_config
from .connectors.public_docs import PublicDocsConnector
from .connectors.git import GitConnector
from .core.document import Document
from .core.chunking import ChunkingStrategy
from .embedding_service import EmbeddingService
from .qdrant_manager import QdrantManager
from datetime import datetime
import uuid

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
        
        # Initialize chunking strategy with global config
        global_config = get_global_config()
        self.chunking_strategy = ChunkingStrategy(
            chunk_size=global_config.chunking["size"],
            chunk_overlap=global_config.chunking["overlap"],
            model_name=global_config.embedding.model
        )
        
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
        
    def _process_git_repos(self, sources: dict) -> List[Document]:
        """Process documents from Git repository sources."""
        documents = []
        
        for source_name, source_config in sources.items():
            try:
                logger.info("Processing Git repository", source=source_name)
                with GitConnector(source_config) as connector:
                    docs = connector.get_documents()
                    documents.extend(docs)
                    
            except Exception as e:
                logger.error("Failed to process Git repository", 
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
                
            # Process Git repository sources
            if config.git_repos:
                git_docs = self._process_git_repos(config.git_repos)
                documents.extend(git_docs)
                
            if not documents:
                logger.warning("No documents were processed")
                return
                
            # Chunk documents
            chunked_documents = []
            for doc in documents:
                chunks = self.chunking_strategy.chunk_document(doc)
                chunked_documents.extend(chunks)
                
            logger.info("Chunked documents", 
                       original_count=len(documents),
                       chunk_count=len(chunked_documents))
                
            # Generate embeddings for all chunks
            logger.info("Generating embeddings", document_count=len(chunked_documents))
            embeddings = self.embedding_service.get_embeddings(
                [doc.content for doc in chunked_documents]
            )
            
            # Prepare points for qDrant
            points = []
            for doc, embedding in zip(chunked_documents, embeddings):
                # Create a unique ID by combining source and chunk index
                point_id = str(uuid.uuid4())
                doc.metadata['original_url'] = doc.metadata.get('url', doc.source)
                
                points.append({
                    "id": point_id,
                    "vector": embedding,
                    "payload": doc.metadata
                })
                
            # Upload to qDrant
            logger.info("Uploading documents to qDrant", point_count=len(points))
            self.qdrant_manager.upsert_points(points)
            
        except Exception as e:
            logger.error("Failed to process documents", error=str(e))
            raise 