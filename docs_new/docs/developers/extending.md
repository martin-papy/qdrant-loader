# Extending QDrant Loader

This guide provides comprehensive instructions for extending QDrant Loader with custom functionality. Whether you need to add support for new data sources, implement custom file processors, or create specialized search capabilities, this guide covers all the extension points and development patterns.

## 🎯 Extension Overview

QDrant Loader is designed with extensibility in mind, offering multiple extension points:

- **Data Source Connectors** - Add support for new data sources
- **File Processors** - Handle new file formats and content types
- **Search Providers** - Implement specialized search algorithms
- **Embedding Providers** - Use different embedding models
- **Storage Backends** - Support alternative vector databases
- **Authentication Providers** - Add custom authentication methods

### Extension Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    QDrant Loader Core                       │
├─────────────────────────────────────────────────────────────┤
│                    Plugin Manager                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Plugin    │ │   Plugin    │ │   Plugin    │          │
│  │ Discovery   │ │ Registry    │ │ Lifecycle   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                    Extension Points                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Connectors  │ │ Processors  │ │   Search    │          │
│  │             │ │             │ │ Providers   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Embeddings  │ │   Storage   │ │    Auth     │          │
│  │             │ │             │ │ Providers   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## 🔌 Plugin Development Framework

### Plugin Structure

All plugins follow a standard structure and implement base interfaces:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from qdrant_loader.plugins.base import BasePlugin

class MyCustomPlugin(BasePlugin):
    """Example custom plugin."""
    
    # Plugin metadata
    name = "my_custom_plugin"
    version = "1.0.0"
    description = "Custom plugin for specialized functionality"
    author = "Your Name"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.custom_setting = config.get("custom_setting", "default")
    
    def initialize(self) -> bool:
        """Initialize plugin resources."""
        # Setup code here
        return True
    
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        # Cleanup code here
        pass
    
    def get_capabilities(self) -> List[str]:
        """Return list of plugin capabilities."""
        return ["custom_capability_1", "custom_capability_2"]
```

### Plugin Registration

Plugins are automatically discovered using entry points in `setup.py`:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="my-qdrant-loader-plugin",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "qdrant_loader.connectors": [
            "my_connector = my_plugin.connectors:MyConnector",
        ],
        "qdrant_loader.processors": [
            "my_processor = my_plugin.processors:MyProcessor",
        ],
        "qdrant_loader.search_providers": [
            "my_search = my_plugin.search:MySearchProvider",
        ],
    },
    install_requires=[
        "qdrant-loader>=1.0.0",
        # Your plugin dependencies
    ],
)
```

## 📊 Custom Data Source Connectors

### Creating a Custom Connector

Data source connectors fetch documents from external systems. Here's how to create one:

```python
from typing import Iterator, Dict, Any, Optional
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.models import Document
import requests
import json

class CustomAPIConnector(BaseConnector):
    """Connector for custom API data source."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config["api_url"]
        self.api_key = config["api_key"]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.batch_size = config.get("batch_size", 100)
    
    def fetch_documents(self) -> Iterator[Document]:
        """Fetch documents from the custom API."""
        offset = 0
        
        while True:
            # Fetch batch of documents
            response = self._fetch_batch(offset)
            
            if not response or not response.get("data"):
                break
            
            # Convert API response to Document objects
            for item in response["data"]:
                document = self._convert_to_document(item)
                if document:
                    yield document
            
            # Check if there are more documents
            if len(response["data"]) < self.batch_size:
                break
            
            offset += self.batch_size
    
    def _fetch_batch(self, offset: int) -> Optional[Dict[str, Any]]:
        """Fetch a batch of documents from the API."""
        try:
            params = {
                "limit": self.batch_size,
                "offset": offset,
                "include_content": True
            }
            
            response = requests.get(
                f"{self.api_url}/documents",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
        
        except requests.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None
    
    def _convert_to_document(self, api_item: Dict[str, Any]) -> Optional[Document]:
        """Convert API response item to Document."""
        try:
            return Document(
                content=api_item["content"],
                metadata={
                    "id": api_item["id"],
                    "title": api_item.get("title", "Untitled"),
                    "author": api_item.get("author"),
                    "created_at": api_item.get("created_at"),
                    "updated_at": api_item.get("updated_at"),
                    "tags": api_item.get("tags", []),
                    "source_url": f"{self.api_url}/documents/{api_item['id']}",
                    "source_type": "custom_api"
                },
                source_type="custom_api"
            )
        except KeyError as e:
            self.logger.warning(f"Missing required field in API response: {e}")
            return None
    
    def supports_incremental(self) -> bool:
        """Check if incremental updates are supported."""
        return True
    
    def get_incremental_documents(self, since: str) -> Iterator[Document]:
        """Fetch documents updated since the given timestamp."""
        params = {
            "updated_since": since,
            "limit": self.batch_size
        }
        
        response = requests.get(
            f"{self.api_url}/documents",
            headers=self.headers,
            params=params
        )
        
        for item in response.json().get("data", []):
            document = self._convert_to_document(item)
            if document:
                yield document
    
    def validate_config(self) -> bool:
        """Validate connector configuration."""
        required_fields = ["api_url", "api_key"]
        
        for field in required_fields:
            if field not in self.config:
                self.logger.error(f"Missing required configuration: {field}")
                return False
        
        # Test API connectivity
        try:
            response = requests.get(
                f"{self.api_url}/health",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException:
            self.logger.error("Cannot connect to API")
            return False
```

### Advanced Connector Features

#### Authentication Handling

```python
class AuthenticatedConnector(BaseConnector):
    """Connector with advanced authentication."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.auth_provider = self._setup_authentication()
    
    def _setup_authentication(self):
        """Setup authentication based on configuration."""
        auth_type = self.config.get("auth_type", "bearer")
        
        if auth_type == "oauth2":
            return OAuth2AuthProvider(self.config)
        elif auth_type == "api_key":
            return APIKeyAuthProvider(self.config)
        elif auth_type == "basic":
            return BasicAuthProvider(self.config)
        else:
            raise ValueError(f"Unsupported auth type: {auth_type}")
    
    def _get_authenticated_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        return self.auth_provider.get_headers()
```

#### Rate Limiting

```python
import time
from functools import wraps

class RateLimitedConnector(BaseConnector):
    """Connector with rate limiting."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.rate_limit = config.get("rate_limit", 10)  # requests per second
        self.last_request_time = 0
    
    def _rate_limit_decorator(self, func):
        """Decorator to enforce rate limiting."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.rate_limit
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    
    @_rate_limit_decorator
    def _make_api_request(self, url: str, **kwargs):
        """Make rate-limited API request."""
        return requests.get(url, **kwargs)
```

## 📄 Custom File Processors

### Creating a Custom Processor

File processors handle specific file formats and extract content:

```python
from typing import Optional, Dict, Any, List
from qdrant_loader.processors.base import BaseProcessor
from qdrant_loader.models import Document
import xml.etree.ElementTree as ET

class XMLProcessor(BaseProcessor):
    """Custom processor for XML files."""
    
    # Define supported file extensions
    supported_extensions = [".xml", ".xsd", ".xsl"]
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.extract_attributes = config.get("extract_attributes", True)
        self.namespace_aware = config.get("namespace_aware", False)
        self.max_depth = config.get("max_depth", 10)
    
    def can_process(self, file_path: str) -> bool:
        """Check if processor can handle the file."""
        return any(file_path.lower().endswith(ext) for ext in self.supported_extensions)
    
    def process_file(self, file_path: str) -> Optional[Document]:
        """Process XML file and extract content."""
        try:
            # Parse XML file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract content and metadata
            content = self._extract_text_content(root)
            metadata = self._extract_metadata(root, file_path)
            
            return Document(
                content=content,
                metadata=metadata,
                source_type="xml_file"
            )
        
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error in {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return None
    
    def _extract_text_content(self, element: ET.Element, depth: int = 0) -> str:
        """Recursively extract text content from XML element."""
        if depth > self.max_depth:
            return ""
        
        content_parts = []
        
        # Add element text
        if element.text and element.text.strip():
            content_parts.append(element.text.strip())
        
        # Add attributes if configured
        if self.extract_attributes and element.attrib:
            attr_text = " ".join(f"{k}={v}" for k, v in element.attrib.items())
            content_parts.append(f"[Attributes: {attr_text}]")
        
        # Recursively process child elements
        for child in element:
            child_content = self._extract_text_content(child, depth + 1)
            if child_content:
                content_parts.append(child_content)
            
            # Add tail text
            if child.tail and child.tail.strip():
                content_parts.append(child.tail.strip())
        
        return "\n".join(content_parts)
    
    def _extract_metadata(self, root: ET.Element, file_path: str) -> Dict[str, Any]:
        """Extract metadata from XML structure."""
        metadata = {
            "file_path": file_path,
            "file_type": "xml",
            "processor": "xml_processor",
            "root_tag": root.tag,
            "namespace": self._extract_namespace(root.tag) if self.namespace_aware else None,
            "element_count": len(list(root.iter())),
            "max_depth": self._calculate_max_depth(root)
        }
        
        # Extract schema information if available
        schema_location = root.get("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation")
        if schema_location:
            metadata["schema_location"] = schema_location
        
        # Extract custom metadata from specific elements
        title_element = root.find(".//title")
        if title_element is not None and title_element.text:
            metadata["title"] = title_element.text.strip()
        
        description_element = root.find(".//description")
        if description_element is not None and description_element.text:
            metadata["description"] = description_element.text.strip()
        
        return metadata
    
    def _extract_namespace(self, tag: str) -> Optional[str]:
        """Extract namespace from XML tag."""
        if tag.startswith("{"):
            return tag[1:tag.find("}")]
        return None
    
    def _calculate_max_depth(self, element: ET.Element, current_depth: int = 0) -> int:
        """Calculate maximum depth of XML structure."""
        if not list(element):
            return current_depth
        
        return max(
            self._calculate_max_depth(child, current_depth + 1)
            for child in element
        )
    
    def get_supported_mime_types(self) -> List[str]:
        """Return supported MIME types."""
        return [
            "application/xml",
            "text/xml",
            "application/xsd+xml",
            "application/xslt+xml"
        ]
```

### Advanced Processor Features

#### Content Chunking

```python
class ChunkingProcessor(BaseProcessor):
    """Processor with advanced chunking capabilities."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.chunk_size = config.get("chunk_size", 1000)
        self.chunk_overlap = config.get("chunk_overlap", 200)
        self.chunking_strategy = config.get("chunking_strategy", "semantic")
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process file and return multiple document chunks."""
        # Extract content
        raw_content = self._extract_content(file_path)
        
        # Create chunks
        chunks = self._create_chunks(raw_content)
        
        # Convert chunks to documents
        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                content=chunk,
                metadata={
                    "file_path": file_path,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                }
            )
            documents.append(doc)
        
        return documents
    
    def _create_chunks(self, content: str) -> List[str]:
        """Create content chunks using specified strategy."""
        if self.chunking_strategy == "semantic":
            return self._semantic_chunking(content)
        elif self.chunking_strategy == "sentence":
            return self._sentence_chunking(content)
        else:
            return self._fixed_size_chunking(content)
    
    def _semantic_chunking(self, content: str) -> List[str]:
        """Create semantically coherent chunks."""
        # Implementation for semantic chunking
        # This could use NLP libraries like spaCy or NLTK
        pass
    
    def _sentence_chunking(self, content: str) -> List[str]:
        """Create chunks based on sentence boundaries."""
        import re
        sentences = re.split(r'[.!?]+', content)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
```

#### Metadata Enrichment

```python
class EnrichedProcessor(BaseProcessor):
    """Processor with metadata enrichment."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.enable_language_detection = config.get("language_detection", True)
        self.enable_sentiment_analysis = config.get("sentiment_analysis", False)
        self.enable_entity_extraction = config.get("entity_extraction", False)
    
    def process_file(self, file_path: str) -> Document:
        """Process file with metadata enrichment."""
        document = super().process_file(file_path)
        
        if document:
            # Enrich metadata
            document.metadata.update(self._enrich_metadata(document.content))
        
        return document
    
    def _enrich_metadata(self, content: str) -> Dict[str, Any]:
        """Enrich document metadata with analysis results."""
        enriched = {}
        
        if self.enable_language_detection:
            enriched["language"] = self._detect_language(content)
        
        if self.enable_sentiment_analysis:
            enriched["sentiment"] = self._analyze_sentiment(content)
        
        if self.enable_entity_extraction:
            enriched["entities"] = self._extract_entities(content)
        
        # Add content statistics
        enriched.update(self._calculate_content_stats(content))
        
        return enriched
    
    def _detect_language(self, content: str) -> str:
        """Detect content language."""
        try:
            from langdetect import detect
            return detect(content)
        except:
            return "unknown"
    
    def _analyze_sentiment(self, content: str) -> Dict[str, float]:
        """Analyze content sentiment."""
        try:
            from textblob import TextBlob
            blob = TextBlob(content)
            return {
                "polarity": blob.sentiment.polarity,
                "subjectivity": blob.sentiment.subjectivity
            }
        except:
            return {"polarity": 0.0, "subjectivity": 0.0}
    
    def _extract_entities(self, content: str) -> List[Dict[str, str]]:
        """Extract named entities from content."""
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(content)
            
            entities = []
            for ent in doc.ents:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
            
            return entities
        except:
            return []
    
    def _calculate_content_stats(self, content: str) -> Dict[str, Any]:
        """Calculate content statistics."""
        words = content.split()
        sentences = content.split('.')
        
        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "character_count": len(content),
            "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "reading_time_minutes": len(words) / 200  # Assuming 200 words per minute
        }
```

## 🔍 Custom Search Providers

### Creating a Custom Search Provider

Search providers implement specialized search algorithms:

```python
from typing import List, Dict, Any, Optional
from qdrant_loader.search.base import BaseSearchProvider
from qdrant_loader.models import SearchResult, Document
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class TFIDFSearchProvider(BaseSearchProvider):
    """Custom search provider using TF-IDF similarity."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vectorizer = TfidfVectorizer(
            max_features=config.get("max_features", 10000),
            stop_words="english",
            ngram_range=config.get("ngram_range", (1, 2))
        )
        self.document_vectors = None
        self.documents = []
    
    def initialize(self, documents: List[Document]) -> None:
        """Initialize search provider with documents."""
        self.documents = documents
        
        # Extract text content
        texts = [doc.content for doc in documents]
        
        # Fit TF-IDF vectorizer and transform documents
        self.document_vectors = self.vectorizer.fit_transform(texts)
        
        self.logger.info(f"Initialized TF-IDF search with {len(documents)} documents")
    
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Execute TF-IDF based search."""
        limit = kwargs.get("limit", 10)
        threshold = kwargs.get("threshold", 0.1)
        
        if not self.document_vectors:
            return []
        
        # Transform query using fitted vectorizer
        query_vector = self.vectorizer.transform([query])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_vector, self.document_vectors).flatten()
        
        # Get top results above threshold
        results = []
        for i, score in enumerate(similarities):
            if score >= threshold:
                result = SearchResult(
                    content=self.documents[i].content,
                    score=float(score),
                    metadata=self.documents[i].metadata,
                    chunk_id=f"tfidf_{i}",
                    document_id=self.documents[i].id or f"doc_{i}"
                )
                results.append(result)
        
        # Sort by score and limit results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return search provider capabilities."""
        return {
            "supports_filters": False,
            "supports_facets": False,
            "supports_highlighting": False,
            "supports_fuzzy_search": True,
            "algorithm": "tf-idf",
            "max_documents": 100000
        }
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add new documents to the search index."""
        self.documents.extend(documents)
        
        # Re-fit vectorizer with all documents
        all_texts = [doc.content for doc in self.documents]
        self.document_vectors = self.vectorizer.fit_transform(all_texts)
    
    def remove_documents(self, document_ids: List[str]) -> None:
        """Remove documents from the search index."""
        # Filter out documents to remove
        self.documents = [
            doc for doc in self.documents 
            if doc.id not in document_ids
        ]
        
        # Re-fit vectorizer
        if self.documents:
            all_texts = [doc.content for doc in self.documents]
            self.document_vectors = self.vectorizer.fit_transform(all_texts)
        else:
            self.document_vectors = None
```

### Advanced Search Features

#### Faceted Search

```python
class FacetedSearchProvider(BaseSearchProvider):
    """Search provider with faceted search capabilities."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.facet_fields = config.get("facet_fields", ["content_type", "author", "language"])
        self.facet_index = {}
    
    def initialize(self, documents: List[Document]) -> None:
        """Initialize with facet indexing."""
        super().initialize(documents)
        self._build_facet_index()
    
    def _build_facet_index(self) -> None:
        """Build facet index for fast filtering."""
        self.facet_index = {}
        
        for field in self.facet_fields:
            self.facet_index[field] = {}
            
            for i, doc in enumerate(self.documents):
                value = doc.metadata.get(field)
                if value:
                    if value not in self.facet_index[field]:
                        self.facet_index[field][value] = []
                    self.facet_index[field][value].append(i)
    
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search with facet filtering."""
        facets = kwargs.get("facets", {})
        
        # Get base search results
        results = super().search(query, **kwargs)
        
        # Apply facet filters
        if facets:
            filtered_results = []
            for result in results:
                if self._matches_facets(result, facets):
                    filtered_results.append(result)
            results = filtered_results
        
        return results
    
    def _matches_facets(self, result: SearchResult, facets: Dict[str, Any]) -> bool:
        """Check if result matches facet criteria."""
        for field, value in facets.items():
            result_value = result.metadata.get(field)
            if isinstance(value, list):
                if result_value not in value:
                    return False
            else:
                if result_value != value:
                    return False
        return True
    
    def get_facets(self, query: str = None) -> Dict[str, Dict[str, int]]:
        """Get facet counts for current document set."""
        facet_counts = {}
        
        for field in self.facet_fields:
            facet_counts[field] = {}
            for value, doc_indices in self.facet_index[field].items():
                facet_counts[field][value] = len(doc_indices)
        
        return facet_counts
```

#### Fuzzy Search

```python
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

class FuzzySearchProvider(BaseSearchProvider):
    """Search provider with fuzzy matching capabilities."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.fuzzy_threshold = config.get("fuzzy_threshold", 70)
        self.fuzzy_ratio_type = config.get("fuzzy_ratio_type", "token_sort_ratio")
    
    def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Search with fuzzy matching."""
        limit = kwargs.get("limit", 10)
        enable_fuzzy = kwargs.get("enable_fuzzy", True)
        
        results = []
        
        for i, doc in enumerate(self.documents):
            # Calculate fuzzy similarity
            if enable_fuzzy:
                fuzzy_score = self._calculate_fuzzy_score(query, doc.content)
            else:
                fuzzy_score = 0
            
            # Calculate exact match score
            exact_score = self._calculate_exact_score(query, doc.content)
            
            # Combine scores
            combined_score = max(fuzzy_score, exact_score)
            
            if combined_score >= self.fuzzy_threshold:
                result = SearchResult(
                    content=doc.content,
                    score=combined_score / 100.0,  # Normalize to 0-1
                    metadata=doc.metadata,
                    chunk_id=f"fuzzy_{i}",
                    document_id=doc.id or f"doc_{i}"
                )
                results.append(result)
        
        # Sort and limit results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def _calculate_fuzzy_score(self, query: str, content: str) -> float:
        """Calculate fuzzy similarity score."""
        if self.fuzzy_ratio_type == "ratio":
            return fuzz.ratio(query.lower(), content.lower())
        elif self.fuzzy_ratio_type == "partial_ratio":
            return fuzz.partial_ratio(query.lower(), content.lower())
        elif self.fuzzy_ratio_type == "token_sort_ratio":
            return fuzz.token_sort_ratio(query.lower(), content.lower())
        elif self.fuzzy_ratio_type == "token_set_ratio":
            return fuzz.token_set_ratio(query.lower(), content.lower())
        else:
            return fuzz.ratio(query.lower(), content.lower())
    
    def _calculate_exact_score(self, query: str, content: str) -> float:
        """Calculate exact match score."""
        query_lower = query.lower()
        content_lower = content.lower()
        
        if query_lower in content_lower:
            # Calculate score based on query length vs content length
            return min(100, (len(query) / len(content)) * 100 + 50)
        
        return 0
```

## 🔐 Custom Authentication Providers

### Creating an Authentication Provider

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
import jwt
from datetime import datetime, timedelta

class BaseAuthProvider(ABC):
    """Base class for authentication providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate user with provided credentials."""
        pass
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers for requests."""
        pass
    
    @abstractmethod
    def refresh_token(self) -> bool:
        """Refresh authentication token if needed."""
        pass

class OAuth2AuthProvider(BaseAuthProvider):
    """OAuth2 authentication provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client_id = config["client_id"]
        self.client_secret = config["client_secret"]
        self.token_url = config["token_url"]
        self.scope = config.get("scope", "read")
        self.access_token = None
        self.refresh_token_value = None
        self.token_expires_at = None
    
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate using OAuth2 flow."""
        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.refresh_token_value = token_data.get("refresh_token")
                
                # Calculate expiration time
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"OAuth2 authentication failed: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get OAuth2 authentication headers."""
        if not self.access_token or self._is_token_expired():
            self.refresh_token()
        
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def refresh_token(self) -> bool:
        """Refresh OAuth2 token."""
        if self.refresh_token_value:
            try:
                response = requests.post(
                    self.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token_value,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.access_token = token_data["access_token"]
                    
                    expires_in = token_data.get("expires_in", 3600)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    return True
            
            except Exception as e:
                self.logger.error(f"Token refresh failed: {e}")
        
        # Fall back to re-authentication
        return self.authenticate({})
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired."""
        if not self.token_expires_at:
            return True
        
        # Add 5-minute buffer
        return datetime.now() >= (self.token_expires_at - timedelta(minutes=5))

class JWTAuthProvider(BaseAuthProvider):
    """JWT-based authentication provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.secret_key = config["secret_key"]
        self.algorithm = config.get("algorithm", "HS256")
        self.token_expiry = config.get("token_expiry_hours", 24)
        self.current_token = None
    
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate and generate JWT token."""
        username = credentials.get("username")
        password = credentials.get("password")
        
        # Validate credentials (implement your validation logic)
        if self._validate_credentials(username, password):
            # Generate JWT token
            payload = {
                "username": username,
                "exp": datetime.utcnow() + timedelta(hours=self.token_expiry),
                "iat": datetime.utcnow()
            }
            
            self.current_token = jwt.encode(
                payload,
                self.secret_key,
                algorithm=self.algorithm
            )
            
            return True
        
        return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get JWT authentication headers."""
        if not self.current_token:
            raise ValueError("No valid token available")
        
        return {"Authorization": f"Bearer {self.current_token}"}
    
    def refresh_token(self) -> bool:
        """Refresh JWT token."""
        if self.current_token:
            try:
                # Decode current token to get user info
                payload = jwt.decode(
                    self.current_token,
                    self.secret_key,
                    algorithms=[self.algorithm]
                )
                
                # Generate new token
                new_payload = {
                    "username": payload["username"],
                    "exp": datetime.utcnow() + timedelta(hours=self.token_expiry),
                    "iat": datetime.utcnow()
                }
                
                self.current_token = jwt.encode(
                    new_payload,
                    self.secret_key,
                    algorithm=self.algorithm
                )
                
                return True
            
            except jwt.ExpiredSignatureError:
                return False
            except jwt.InvalidTokenError:
                return False
        
        return False
    
    def _validate_credentials(self, username: str, password: str) -> bool:
        """Validate user credentials."""
        # Implement your credential validation logic here
        # This could check against a database, LDAP, etc.
        return username and password  # Simplified example
```

## 📦 Plugin Packaging and Distribution

### Plugin Project Structure

```
my-qdrant-loader-plugin/
├── setup.py
├── README.md
├── requirements.txt
├── my_plugin/
│   ├── __init__.py
│   ├── connectors/
│   │   ├── __init__.py
│   │   └── my_connector.py
│   ├── processors/
│   │   ├── __init__.py
│   │   └── my_processor.py
│   ├── search/
│   │   ├── __init__.py
│   │   └── my_search_provider.py
│   └── auth/
│       ├── __init__.py
│       └── my_auth_provider.py
├── tests/
│   ├── __init__.py
│   ├── test_connectors.py
│   ├── test_processors.py
│   └── test_search.py
└── docs/
    ├── installation.md
    ├── configuration.md
    └── usage.md
```

### Setup Configuration

```python
# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="my-qdrant-loader-plugin",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Custom plugin for QDrant Loader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/my-qdrant-loader-plugin",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "qdrant_loader.connectors": [
            "my_api = my_plugin.connectors.my_connector:CustomAPIConnector",
        ],
        "qdrant_loader.processors": [
            "xml = my_plugin.processors.my_processor:XMLProcessor",
        ],
        "qdrant_loader.search_providers": [
            "tfidf = my_plugin.search.my_search_provider:TFIDFSearchProvider",
            "fuzzy = my_plugin.search.my_search_provider:FuzzySearchProvider",
        ],
        "qdrant_loader.auth_providers": [
            "oauth2 = my_plugin.auth.my_auth_provider:OAuth2AuthProvider",
            "jwt = my_plugin.auth.my_auth_provider:JWTAuthProvider",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-mock>=3.0",
        ],
    },
)
```

### Plugin Testing

```python
# tests/test_connectors.py
import pytest
from unittest.mock import Mock, patch
from my_plugin.connectors.my_connector import CustomAPIConnector

class TestCustomAPIConnector:
    """Test suite for CustomAPIConnector."""
    
    @pytest.fixture
    def connector_config(self):
        """Test configuration for connector."""
        return {
            "api_url": "https://api.example.com",
            "api_key": "test_key",
            "batch_size": 10
        }
    
    @pytest.fixture
    def connector(self, connector_config):
        """Connector instance for testing."""
        return CustomAPIConnector(connector_config)
    
    def test_connector_initialization(self, connector):
        """Test connector initialization."""
        assert connector.api_url == "https://api.example.com"
        assert connector.api_key == "test_key"
        assert connector.batch_size == 10
    
    @patch('requests.get')
    def test_fetch_documents(self, mock_get, connector):
        """Test document fetching."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "1",
                    "content": "Test content 1",
                    "title": "Test Document 1"
                },
                {
                    "id": "2",
                    "content": "Test content 2",
                    "title": "Test Document 2"
                }
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test document fetching
        documents = list(connector.fetch_documents())
        
        assert len(documents) == 2
        assert documents[0].content == "Test content 1"
        assert documents[0].metadata["title"] == "Test Document 1"
    
    def test_validate_config_success(self, connector):
        """Test successful configuration validation."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            assert connector.validate_config() is True
    
    def test_validate_config_failure(self, connector):
        """Test failed configuration validation."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            assert connector.validate_config() is False
```

## 🔗 Integration Examples

### Using Custom Extensions

```python
from qdrant_loader import QDrantLoader
from qdrant_loader.config import Config

# Configuration with custom extensions
config_dict = {
    "qdrant": {
        "url": "http://localhost:6333"
    },
    "data_sources": {
        "my_api": {
            "connector_type": "my_api",  # References plugin entry point
            "api_url": "https://api.example.com",
            "api_key": "your_api_key"
        }
    },
    "processing": {
        "processors": {
            "xml": {  # References plugin entry point
                "extract_attributes": True,
                "namespace_aware": True
            }
        }
    },
    "search": {
        "providers": {
            "tfidf": {  # References plugin entry point
                "max_features": 5000,
                "ngram_range": [1, 2]
            }
        }
    }
}

config = Config.from_dict(config_dict)
loader = QDrantLoader(config)

# Use custom connector
result = loader.load_source("my_api")

# Use custom search provider
results = loader.search("query", search_provider="tfidf")
```

## 🔗 Related Documentation

- **[Architecture Guide](./architecture.md)** - System design and components
- **[API Reference](./api-reference.md)** - Complete API documentation
- **[Testing Guide](./testing.md)** - Testing strategies and tools
- **[Deployment Guide](./deployment.md)** - Production deployment
- **[Configuration Reference](../users/configuration/config-file-reference.md)** - Configuration options

---

**Ready to extend QDrant Loader?** Start with the extension type that matches your needs, use the provided templates and examples, and refer to the [API Reference](./api-reference.md) for detailed interface specifications.

**Need help with testing?** Check the [Testing Guide](./testing.md) for comprehensive testing strategies for your custom extensions.
