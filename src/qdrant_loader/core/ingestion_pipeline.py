"""Pipeline for processing and ingesting documents from various sources."""

import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import structlog
from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.core.embedding_service import EmbeddingService
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.core.chunking_strategy import ChunkingStrategy
from qdrant_loader.core.document import Document
from qdrant_loader.connectors.public_docs import PublicDocsConnector
from qdrant_loader.connectors.git import GitConnector
from qdrant_loader.connectors.confluence import ConfluenceConnector
from qdrant_loader.connectors.jira import JiraConnector
from qdrant_loader.core.qdrant_manager import QdrantConnectionError

logger = structlog.get_logger()

class IngestionPipeline:
    """Pipeline for processing and ingesting documents from various sources."""
    
    def __init__(self, settings: Settings):
        """Initialize the ingestion pipeline.
        
        Args:
            settings: The application settings.
        
        Raises:
            Exception: If settings are not available.
        """
        if not settings:
            raise Exception("Failed to initialize pipeline: Settings not available. Please check your environment variables.")
        
        self.settings = settings
        self.embedding_service = EmbeddingService(settings)
        self.qdrant_manager = QdrantManager(settings)
        self.chunking_strategy = ChunkingStrategy(
            settings=settings,
            chunk_size=settings.global_config.chunking.chunk_size,
            chunk_overlap=settings.global_config.chunking.chunk_overlap
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
                        url=str(source_config.base_url),  # Convert HttpUrl to string
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
                raise  # Re-raise the exception to trigger error handling
                
        return documents
        
    def _process_git_repos(self, git_repos: dict) -> List[Document]:
        """Process documents from Git repository sources."""
        documents = []
        for repo_name, repo_config in git_repos.items():
            try:
                with GitConnector(repo_config) as connector:
                    repo_docs = connector.get_documents()
                    documents.extend(repo_docs)
                    logger.info(f"Processed Git repository: {repo_name}", 
                              document_count=len(repo_docs))
            except Exception as e:
                logger.error(f"Failed to process Git repository {repo_name}", 
                           error=str(e))
        return documents

    def _process_confluence(self, confluence_spaces: dict) -> List[Document]:
        """Process documents from Confluence sources.
        
        Args:
            confluence_spaces: Dictionary of Confluence space configurations
            
        Returns:
            List[Document]: List of processed documents
        """
        documents = []
        for space_name, space_config in confluence_spaces.items():
            try:
                connector = ConfluenceConnector(space_config)
                space_docs = connector.get_documents()
                documents.extend(space_docs)
                logger.info(f"Processed Confluence space: {space_name}", 
                          document_count=len(space_docs))
            except Exception as e:
                logger.error(f"Failed to process Confluence space {space_name}", 
                           error=str(e))
        return documents

    async def _process_jira(self, jira_projects: dict) -> List[Document]:
        """Process documents from JIRA sources.
        
        Args:
            jira_projects: Dictionary of JIRA project configurations
            
        Returns:
            List[Document]: List of processed documents
        """
        documents = []
        for project_name, project_config in jira_projects.items():
            try:
                connector = JiraConnector(project_config)
                
                # Collect all issues
                issues = []
                async for issue in connector.get_issues():
                    issues.append(issue)
                
                # Convert issues to documents
                for issue in issues:
                    content = f"{issue.summary}\n\n{issue.description or ''}"
                    document = Document(
                        id=issue.id,
                        content=content,
                        source=project_name,
                        source_type="jira",
                        url=f"{project_config.base_url}/browse/{issue.key}",
                        last_updated=issue.updated,
                        metadata={
                            "project": project_name,
                            "issue_type": issue.issue_type,
                            "status": issue.status,
                            "key": issue.key,
                            "priority": issue.priority,
                            "labels": issue.labels,
                            "reporter": issue.reporter.display_name if issue.reporter else None,
                            "assignee": issue.assignee.display_name if issue.assignee else None,
                            "created": issue.created.isoformat(),
                            "updated": issue.updated.isoformat(),
                            "parent_key": issue.parent_key,
                            "subtasks": issue.subtasks,
                            "linked_issues": issue.linked_issues
                        }
                    )
                    documents.append(document)
                
                logger.info(f"Processed JIRA project: {project_name}", 
                          document_count=len(documents))
            except Exception as e:
                logger.error(f"Failed to process JIRA project {project_name}", 
                           error=str(e))
        return documents

    def _filter_sources(self, config: SourcesConfig, source_type: Optional[str] = None, source_name: Optional[str] = None) -> SourcesConfig:
        """Filter sources based on type and name.
        
        Args:
            config: Configuration containing source definitions
            source_type: Optional type of source to process (confluence, git, public-docs, jira)
            source_name: Optional specific source name to process
        
        Returns:
            SourcesConfig: Filtered configuration
        """
        filtered_config = SourcesConfig()
        
        if not source_type:
            return config
        
        if source_type == "public-docs":
            if source_name:
                filtered_config.public_docs = {source_name: config.public_docs[source_name]} if source_name in config.public_docs else {}
            else:
                filtered_config.public_docs = config.public_docs
        elif source_type == "git":
            if source_name:
                filtered_config.git_repos = {source_name: config.git_repos[source_name]} if source_name in config.git_repos else {}
            else:
                filtered_config.git_repos = config.git_repos
        elif source_type == "confluence":
            if source_name:
                filtered_config.confluence = {source_name: config.confluence[source_name]} if source_name in config.confluence else {}
            else:
                filtered_config.confluence = config.confluence
        elif source_type == "jira":
            if source_name:
                filtered_config.jira = {source_name: config.jira[source_name]} if source_name in config.jira else {}
            else:
                filtered_config.jira = config.jira
        
        return filtered_config

    async def process_documents(self, config: SourcesConfig, source_type: Optional[str] = None, source_name: Optional[str] = None) -> List[Document]:
        """Process and ingest documents from the specified sources.
        
        Args:
            config: Configuration containing source definitions
            source_type: Optional type of source to process (confluence, git, public-docs, jira)
            source_name: Optional specific source name to process
        
        Returns:
            List[Document]: List of processed documents
        
        Raises:
            QdrantConnectionError: If connection to Qdrant fails
            Exception: If document processing fails
        """
        try:
            # Filter sources based on type and name
            filtered_config = self._filter_sources(config, source_type, source_name)
            
            if not any([filtered_config.confluence, filtered_config.git_repos, filtered_config.public_docs, filtered_config.jira]):
                logger.warning("No sources to process after filtering",
                             source_type=source_type,
                             source_name=source_name)
                return []
            
            documents = []
            
            # Process public documentation sources
            if filtered_config.public_docs:
                try:
                    public_docs = self._process_public_docs(filtered_config.public_docs)
                    documents.extend(public_docs)
                except Exception as e:
                    logger.error("Failed to process public docs source", source="public-docs", error=str(e))
                    raise
            
            # Process Git repository sources
            if filtered_config.git_repos:
                try:
                    git_docs = self._process_git_repos(filtered_config.git_repos)
                    documents.extend(git_docs)
                except Exception as e:
                    logger.error("Failed to process git repos source", source="git-repos", error=str(e))
                    raise
            
            # Process Confluence sources
            if filtered_config.confluence:
                try:
                    confluence_docs = self._process_confluence(filtered_config.confluence)
                    documents.extend(confluence_docs)
                except Exception as e:
                    logger.error("Failed to process confluence source", source="confluence", error=str(e))
                    raise
            
            # Process JIRA sources
            if filtered_config.jira:
                try:
                    # Since we're already in an async context, just await the coroutine
                    jira_docs = await self._process_jira(filtered_config.jira)
                    documents.extend(jira_docs)
                except Exception as e:
                    logger.error("Failed to process JIRA source", source="jira", error=str(e))
                    raise
            
            if not documents:
                logger.warning("No documents were processed")
                return []
            
            # Chunk documents
            chunked_documents = []
            for doc in documents:
                chunks = self.chunking_strategy.chunk_document(doc)
                chunked_documents.extend(chunks)
            
            logger.info("Chunked documents",
                       original_count=len(documents),
                       chunk_count=len(chunked_documents))
            
            # Process documents in batches
            batch_size = self.settings.global_config.embedding.batch_size
            points = []
            
            for i in range(0, len(chunked_documents), batch_size):
                batch = chunked_documents[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(chunked_documents) + batch_size - 1)//batch_size}")
                
                # Generate embeddings for the batch
                embeddings = self.embedding_service.get_embeddings(
                    [doc.content for doc in batch]
                )
                
                # Create points for the batch
                for doc, embedding in zip(batch, embeddings):
                    point_id = doc.id or str(uuid.uuid4())
                    doc.metadata['original_url'] = doc.metadata.get('url', doc.source)
                    
                    points.append({
                        "id": point_id,
                        "vector": embedding,
                        "payload": {
                            "content": doc.content,
                            "source": doc.source,
                            "source_type": doc.source_type,
                            "url": doc.url,
                            "last_updated": doc.last_updated.isoformat() if doc.last_updated else None,
                            "metadata": doc.metadata
                        }
                    })
            
            # Upload points to qDrant
            self.qdrant_manager.upsert_points(points)
            logger.info("Successfully processed and uploaded documents", document_count=len(documents))
            return documents
            
        except QdrantConnectionError as e:
            logger.error("connection_failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to process documents", error=str(e))
            raise 