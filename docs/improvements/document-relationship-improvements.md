# Document Relationship Preservation Improvements

## Overview

This document provides concrete implementation strategies for improving document relationship preservation across all data sources in the qdrant-loader system, addressing the critical gaps identified in the relationship analysis.

## Priority Implementation Plan

### Phase 1: File System Hierarchy Foundation (Weeks 1-4)

**Objective**: Implement explicit folder hierarchy preservation for Git and Local File connectors

#### 1.1 Enhanced File System Metadata Model

Create a hierarchical metadata model for file systems:

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/base/models.py
@dataclass
class FileSystemHierarchy:
    """Represents file system hierarchy relationships."""
    
    # Path components
    full_path: str                    # Complete file path
    relative_path: str               # Path relative to root
    directory_path: str              # Parent directory path
    filename: str                    # File name with extension
    
    # Hierarchy relationships
    parent_directory_id: str | None  # Parent directory unique ID
    root_distance: int               # Depth from repository/project root
    path_components: list[str]       # Path split into components
    
    # Sibling and relationship info
    sibling_files: list[str]         # Files in same directory
    child_directories: list[str]     # Subdirectories (for directories)
    
    # Breadcrumb navigation
    breadcrumb_path: list[str]       # Directory breadcrumb
    breadcrumb_text: str            # Human-readable path
    
    # Project organization
    is_readme: bool                  # Is this a README file
    is_config: bool                  # Is this a configuration file
    project_structure_role: str      # src, docs, tests, etc.
```

#### 1.2 Directory-Level Metadata Extraction

Implement directory analysis during file processing:

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/base/directory_analyzer.py
class DirectoryAnalyzer:
    """Analyzes directory structure and relationships."""
    
    def analyze_directory_structure(self, root_path: str) -> Dict[str, DirectoryInfo]:
        """Build complete directory structure map."""
        directories = {}
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            rel_path = os.path.relpath(dirpath, root_path)
            
            # Create directory info
            dir_info = DirectoryInfo(
                path=rel_path,
                parent_path=os.path.dirname(rel_path) if rel_path != "." else None,
                children_dirs=dirnames,
                children_files=filenames,
                depth=len(rel_path.split(os.sep)) if rel_path != "." else 0,
                project_role=self._identify_directory_role(rel_path, filenames)
            )
            
            directories[rel_path] = dir_info
            
        return directories
    
    def _identify_directory_role(self, path: str, files: list[str]) -> str:
        """Identify the role of a directory in project structure."""
        path_lower = path.lower()
        
        # Common project structure patterns
        if any(pattern in path_lower for pattern in ['src', 'source', 'lib']):
            return "source_code"
        elif any(pattern in path_lower for pattern in ['test', 'spec']):
            return "tests"
        elif any(pattern in path_lower for pattern in ['doc', 'documentation']):
            return "documentation"
        elif any(pattern in path_lower for pattern in ['config', 'conf', 'settings']):
            return "configuration"
        elif 'readme' in [f.lower() for f in files]:
            return "project_root"
        else:
            return "general"
```

#### 1.3 Enhanced Git Connector Implementation

Update Git connector to preserve hierarchy:

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/git/enhanced_connector.py
class EnhancedGitConnector(GitConnector):
    """Enhanced Git connector with hierarchy preservation."""
    
    def __init__(self, config: GitProjectConfig):
        super().__init__(config)
        self.directory_analyzer = DirectoryAnalyzer()
        self.directory_structure = {}
    
    async def __aenter__(self):
        """Enhanced initialization with directory analysis."""
        await super().__aenter__()
        
        # Analyze directory structure after cloning
        self.directory_structure = self.directory_analyzer.analyze_directory_structure(
            self.temp_dir
        )
    
    def _process_file(self, file_path: str) -> Document:
        """Enhanced file processing with hierarchy metadata."""
        document = super()._process_file(file_path)
        
        # Add hierarchical metadata
        hierarchy_metadata = self._extract_file_hierarchy(file_path)
        document.metadata.update(hierarchy_metadata)
        
        return document
    
    def _extract_file_hierarchy(self, file_path: str) -> Dict[str, Any]:
        """Extract hierarchical relationship metadata for a file."""
        rel_path = os.path.relpath(file_path, self.temp_dir)
        directory_path = os.path.dirname(rel_path)
        
        # Get directory info
        dir_info = self.directory_structure.get(directory_path, None)
        
        # Build hierarchy metadata
        hierarchy = FileSystemHierarchy(
            full_path=file_path,
            relative_path=rel_path,
            directory_path=directory_path,
            filename=os.path.basename(file_path),
            parent_directory_id=self._generate_directory_id(directory_path),
            root_distance=len(rel_path.split(os.sep)) - 1,
            path_components=rel_path.split(os.sep)[:-1],
            sibling_files=dir_info.children_files if dir_info else [],
            breadcrumb_path=rel_path.split(os.sep)[:-1],
            breadcrumb_text=" > ".join(rel_path.split(os.sep)[:-1]),
            is_readme="readme" in os.path.basename(file_path).lower(),
            is_config=self._is_config_file(file_path),
            project_structure_role=dir_info.project_role if dir_info else "general"
        )
        
        return {
            "file_hierarchy": asdict(hierarchy),
            "parent_directory_id": hierarchy.parent_directory_id,
            "directory_path": hierarchy.directory_path,
            "root_distance": hierarchy.root_distance,
            "breadcrumb_text": hierarchy.breadcrumb_text,
            "sibling_files": hierarchy.sibling_files,
            "project_role": hierarchy.project_structure_role,
            "is_readme": hierarchy.is_readme,
            "is_config": hierarchy.is_config,
        }
```

#### 1.4 Local File Connector Enhancement

Similar enhancements for local file connector:

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/localfile/enhanced_connector.py
class EnhancedLocalFileConnector(LocalFileConnector):
    """Enhanced Local File connector with hierarchy preservation."""
    
    def __init__(self, config: LocalFileConfig):
        super().__init__(config)
        self.directory_analyzer = DirectoryAnalyzer()
        self.directory_structure = {}
    
    async def get_documents(self) -> list[Document]:
        """Enhanced document retrieval with hierarchy analysis."""
        # Analyze directory structure first
        self.directory_structure = self.directory_analyzer.analyze_directory_structure(
            self.config.base_path
        )
        
        # Process files with hierarchy context
        return await super().get_documents()
```

### Phase 2: Chunking Strategy Relationship Standardization (Weeks 5-8)

**Objective**: Standardize relationship preservation across all chunking strategies

#### 2.1 Universal Relationship Metadata Schema

Define standardized relationship metadata:

```python
# packages/qdrant-loader/src/qdrant_loader/core/chunking/relationship_metadata.py
@dataclass
class DocumentRelationshipMetadata:
    """Standardized relationship metadata for all document types."""
    
    # Universal relationships
    parent_document_id: str | None   # Direct parent document
    child_document_ids: list[str]    # Direct child documents
    sibling_document_ids: list[str]  # Sibling documents
    
    # Hierarchical context
    hierarchy_depth: int             # Depth in hierarchy
    hierarchy_path: list[str]        # Path from root to current
    breadcrumb_text: str            # Human-readable path
    
    # Cross-references
    referenced_document_ids: list[str]  # Documents this references
    referencing_document_ids: list[str] # Documents that reference this
    
    # Contextual grouping
    project_id: str | None          # Project/repository grouping
    source_type: str                # jira, confluence, git, localfile
    content_type: str               # Issue, page, file, attachment
    
    # Attachment relationships
    is_attachment: bool             # Is this an attachment
    attachment_parent_id: str | None # Parent document for attachments
    has_attachments: bool           # Does this have attachments
    attachment_ids: list[str]       # List of attachment document IDs
    
    # Semantic relationships (populated by cross-document intelligence)
    similar_document_ids: list[str] # Semantically similar documents
    complementary_document_ids: list[str] # Complementary documents
    conflicting_document_ids: list[str]  # Conflicting documents
```

#### 2.2 Relationship-Aware Base Chunking Strategy

Enhance base chunking strategy:

```python
# packages/qdrant-loader/src/qdrant_loader/core/chunking/strategy/base_strategy.py
class RelationshipAwareBaseChunkingStrategy(BaseChunkingStrategy):
    """Enhanced base strategy with relationship preservation."""
    
    def create_chunk_with_relationships(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        chunk_metadata: Dict[str, Any] = None
    ) -> Document:
        """Create chunk document with relationship preservation."""
        
        chunk_doc = self._create_chunk_document(
            original_doc, chunk_content, chunk_index, total_chunks
        )
        
        # Extract and preserve relationships
        relationship_metadata = self._extract_chunk_relationships(
            original_doc, chunk_content, chunk_metadata or {}
        )
        
        chunk_doc.metadata.update(relationship_metadata)
        return chunk_doc
    
    def _extract_chunk_relationships(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract relationship metadata for chunk."""
        
        # Build relationship metadata based on source type
        relationships = DocumentRelationshipMetadata(
            parent_document_id=original_doc.id,
            child_document_ids=[],
            sibling_document_ids=self._find_sibling_chunks(original_doc),
            hierarchy_depth=original_doc.metadata.get("root_distance", 0),
            hierarchy_path=original_doc.metadata.get("breadcrumb_path", []),
            breadcrumb_text=original_doc.metadata.get("breadcrumb_text", ""),
            referenced_document_ids=self._extract_document_references(chunk_content),
            referencing_document_ids=[],
            project_id=original_doc.metadata.get("project_id"),
            source_type=original_doc.source_type.value,
            content_type=self._determine_content_type(original_doc),
            is_attachment=original_doc.metadata.get("is_attachment", False),
            attachment_parent_id=original_doc.metadata.get("parent_document_id"),
            has_attachments=bool(original_doc.metadata.get("attachments", [])),
            attachment_ids=self._extract_attachment_ids(original_doc),
            similar_document_ids=[],
            complementary_document_ids=[],
            conflicting_document_ids=[]
        )
        
        return asdict(relationships)
```

#### 2.3 Strategy-Specific Relationship Enhancement

Update each chunking strategy:

```python
# Enhanced Default Strategy
class RelationshipAwareDefaultChunkingStrategy(RelationshipAwareBaseChunkingStrategy):
    """Default strategy with relationship preservation."""
    
    def _extract_chunk_relationships(self, original_doc, chunk_content, chunk_metadata):
        """Default text relationship extraction."""
        base_relationships = super()._extract_chunk_relationships(
            original_doc, chunk_content, chunk_metadata
        )
        
        # Add text-specific relationship extraction
        base_relationships.update({
            "paragraph_references": self._extract_paragraph_references(chunk_content),
            "section_context": self._extract_section_context(chunk_content),
        })
        
        return base_relationships

# Enhanced HTML Strategy  
class RelationshipAwareHTMLChunkingStrategy(RelationshipAwareBaseChunkingStrategy):
    """HTML strategy with DOM relationship preservation."""
    
    def _extract_chunk_relationships(self, original_doc, chunk_content, chunk_metadata):
        """HTML-specific relationship extraction."""
        base_relationships = super()._extract_chunk_relationships(
            original_doc, chunk_content, chunk_metadata
        )
        
        # Add HTML-specific relationships
        base_relationships.update({
            "dom_parent_path": chunk_metadata.get("dom_path", ""),
            "html_references": self._extract_html_links(chunk_content),
            "semantic_element_type": chunk_metadata.get("section_type", ""),
        })
        
        return base_relationships
```

### Phase 3: Enhanced Cross-Document Intelligence (Weeks 9-12)

**Objective**: Leverage improved relationship metadata for better retrieval

#### 3.1 File System Hierarchy Search

Implement hierarchy search for file systems:

```python
# packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/search/enhanced/file_hierarchy.py
class FileSystemHierarchySearch:
    """Hierarchy search capabilities for file system sources."""
    
    def find_related_files(
        self,
        target_file_path: str,
        documents: List[SearchResult],
        relationship_types: List[str] = None
    ) -> Dict[str, List[SearchResult]]:
        """Find related files in file system hierarchy."""
        
        if relationship_types is None:
            relationship_types = ["siblings", "parent_directory", "subdirectories", "project_related"]
        
        related_files = {rel_type: [] for rel_type in relationship_types}
        
        target_directory = os.path.dirname(target_file_path)
        
        for doc in documents:
            if doc.source_type not in ["git", "localfile"]:
                continue
                
            doc_path = doc.metadata.get("relative_path", "")
            doc_directory = os.path.dirname(doc_path)
            
            # Sibling files (same directory)
            if "siblings" in relationship_types and doc_directory == target_directory:
                related_files["siblings"].append(doc)
            
            # Parent directory files
            if "parent_directory" in relationship_types:
                if target_directory.startswith(doc_directory + "/"):
                    related_files["parent_directory"].append(doc)
            
            # Subdirectory files
            if "subdirectories" in relationship_types:
                if doc_directory.startswith(target_directory + "/"):
                    related_files["subdirectories"].append(doc)
            
            # Project-related files (README, config files)
            if "project_related" in relationship_types:
                if (doc.metadata.get("is_readme") or 
                    doc.metadata.get("is_config") or
                    doc.metadata.get("project_role") == "project_root"):
                    related_files["project_related"].append(doc)
        
        return related_files
    
    def build_project_structure_map(
        self,
        documents: List[SearchResult]
    ) -> Dict[str, Any]:
        """Build a map of project structure from file documents."""
        
        structure = defaultdict(lambda: {
            "files": [],
            "subdirectories": [],
            "role": "general",
            "readme_files": [],
            "config_files": []
        })
        
        for doc in documents:
            if doc.source_type not in ["git", "localfile"]:
                continue
                
            dir_path = os.path.dirname(doc.metadata.get("relative_path", ""))
            
            structure[dir_path]["files"].append(doc)
            
            if doc.metadata.get("is_readme"):
                structure[dir_path]["readme_files"].append(doc)
            if doc.metadata.get("is_config"):
                structure[dir_path]["config_files"].append(doc)
                
            role = doc.metadata.get("project_role", "general")
            if role != "general":
                structure[dir_path]["role"] = role
        
        return dict(structure)
```

#### 3.2 Enhanced Relationship Detection

Improve cross-document intelligence:

```python
# Enhanced CrossDocumentIntelligenceEngine
class EnhancedCrossDocumentIntelligenceEngine(CrossDocumentIntelligenceEngine):
    """Enhanced engine with file system relationship support."""
    
    def __init__(self):
        super().__init__()
        self.file_hierarchy_search = FileSystemHierarchySearch()
    
    def find_document_relationships(
        self,
        target_doc_id: str,
        documents: List[SearchResult],
        relationship_types: List[RelationshipType] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Enhanced relationship finding with file system support."""
        
        base_relationships = super().find_document_relationships(
            target_doc_id, documents, relationship_types
        )
        
        # Add file system hierarchy relationships
        target_doc = self._find_document_by_id(target_doc_id, documents)
        if target_doc and target_doc.source_type in ["git", "localfile"]:
            file_relationships = self.file_hierarchy_search.find_related_files(
                target_doc.metadata.get("relative_path", ""),
                documents
            )
            
            # Merge file system relationships
            for rel_type, related_docs in file_relationships.items():
                if rel_type not in base_relationships:
                    base_relationships[rel_type] = []
                
                base_relationships[rel_type].extend([
                    {
                        "document_id": f"{doc.source_type}:{doc.source_title}",
                        "relationship": rel_type,
                        "explanation": f"File system {rel_type} relationship",
                        "score": 1.0
                    }
                    for doc in related_docs[:5]  # Limit results
                ])
        
        return base_relationships
```

### Phase 4: Integration and Testing (Weeks 13-16)

#### 4.1 Configuration Updates

Add relationship-aware configuration:

```yaml
# Enhanced configuration schema
chunking:
  preserve_relationships: true
  relationship_metadata:
    extract_cross_references: true
    build_hierarchy_breadcrumbs: true
    detect_sibling_relationships: true
    
  strategies:
    git:
      analyze_directory_structure: true
      preserve_folder_hierarchy: true
      extract_project_structure: true
      include_readme_relationships: true
      
    localfile:
      analyze_directory_structure: true
      preserve_folder_hierarchy: true
      extract_project_structure: true
      
search:
  hierarchy_search:
    enabled_for_file_systems: true
    max_hierarchy_depth: 10
    include_sibling_discovery: true
```

#### 4.2 Migration Strategy

Implement backward-compatible migration:

```python
# Migration for existing documents
class RelationshipMetadataMigration:
    """Migrate existing documents to include relationship metadata."""
    
    async def migrate_existing_documents(self, project_id: str):
        """Add relationship metadata to existing documents."""
        
        # Get all documents for project
        documents = await self.document_store.get_documents_by_project(project_id)
        
        # Group by source type
        grouped_docs = self._group_by_source_type(documents)
        
        # Migrate each source type
        for source_type, docs in grouped_docs.items():
            if source_type in ["git", "localfile"]:
                await self._migrate_file_system_documents(docs)
            elif source_type == "confluence":
                await self._migrate_confluence_documents(docs)
            elif source_type == "jira":
                await self._migrate_jira_documents(docs)
    
    async def _migrate_file_system_documents(self, documents: List[Document]):
        """Add file system hierarchy metadata to existing documents."""
        
        # Build directory structure from existing documents
        directory_analyzer = DirectoryAnalyzer()
        
        for doc in documents:
            file_path = doc.metadata.get("file_path", "")
            if file_path:
                # Generate hierarchy metadata
                hierarchy_metadata = self._generate_hierarchy_metadata(file_path, documents)
                
                # Update document metadata
                doc.metadata.update(hierarchy_metadata)
                await self.document_store.update_document(doc)
```

## Implementation Timeline

### Week 1-2: Foundation
- Implement `FileSystemHierarchy` model
- Create `DirectoryAnalyzer` class
- Update configuration schema

### Week 3-4: Git & Local File Enhancement
- Enhance Git connector with hierarchy preservation
- Enhance Local File connector with hierarchy preservation
- Add hierarchy metadata extraction

### Week 5-6: Chunking Strategy Standardization
- Implement `DocumentRelationshipMetadata` schema
- Create `RelationshipAwareBaseChunkingStrategy`
- Update all chunking strategies

### Week 7-8: Cross-Strategy Integration
- Standardize relationship metadata across strategies
- Implement relationship-aware chunk creation
- Add cross-reference extraction

### Week 9-10: Enhanced Search Capabilities
- Implement `FileSystemHierarchySearch`
- Enhance `CrossDocumentIntelligenceEngine`
- Add file system hierarchy search support

### Week 11-12: MCP Server Integration
- Add hierarchy search tools for file systems
- Implement project structure visualization
- Enhance search result presentation

### Week 13-14: Testing & Migration
- Comprehensive testing of all relationship features
- Implement migration for existing documents
- Performance optimization

### Week 15-16: Documentation & Polish
- Complete documentation updates
- User guides for new relationship features
- Final testing and bug fixes

## Success Metrics

### Technical Metrics
- ✅ File system documents include explicit hierarchy relationships
- ✅ All chunking strategies preserve relationship metadata consistently
- ✅ Cross-document intelligence leverages enhanced metadata
- ✅ Search tools support file system hierarchy navigation

### User Experience Metrics
- ✅ Users can navigate file system hierarchies semantically
- ✅ Related files are discoverable within project structures
- ✅ README and configuration files are properly associated
- ✅ Attachment relationships are consistent across all sources

### Performance Metrics
- ✅ Relationship extraction adds < 20% to ingestion time
- ✅ Enhanced metadata increases storage by < 30%
- ✅ Search performance maintained or improved
- ✅ Memory usage remains within acceptable limits

## Conclusion

This implementation plan addresses the critical gaps in document relationship preservation, particularly for file system sources. By implementing explicit hierarchy preservation, standardizing relationship metadata across chunking strategies, and enhancing cross-document intelligence, the qdrant-loader system will provide consistent, high-quality relationship preservation across all data sources.

The phased approach ensures backward compatibility while systematically improving relationship preservation capabilities, ultimately enabling users to navigate and understand document relationships regardless of their source type. 