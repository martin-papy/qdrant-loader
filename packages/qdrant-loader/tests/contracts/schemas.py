"""Contract schemas for validating component interfaces.

This module defines Pydantic schemas that represent the expected contracts
between major system components including databases, AI services, and pipelines.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Core Data Contracts
# ============================================================================

class EntityTypeContract(str, Enum):
    """Contract for supported entity types."""
    SERVICE = "Service"
    DATABASE = "Database"
    TEAM = "Team"
    PERSON = "Person"
    ORGANIZATION = "Organization"
    PROJECT = "Project"
    CONCEPT = "Concept"
    TECHNOLOGY = "Technology"
    API = "API"
    ENDPOINT = "Endpoint"


class RelationshipTypeContract(str, Enum):
    """Contract for supported relationship types."""
    CONTAINS = "contains"
    REFERENCES = "references"
    AUTHORED_BY = "authored_by"
    BELONGS_TO = "belongs_to"
    RELATED_TO = "related_to"
    DERIVED_FROM = "derived_from"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    USES = "uses"
    MANAGES = "manages"


class TemporalInfoContract(BaseModel):
    """Contract for temporal information in entities and relationships."""
    
    valid_from: datetime
    valid_to: Optional[datetime] = None
    transaction_time: datetime
    version: int = Field(ge=1)
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None

    @field_validator('valid_to')
    @classmethod
    def valid_to_after_valid_from(cls, v, info):
        if v is not None and 'valid_from' in info.data and v <= info.data['valid_from']:
            raise ValueError('valid_to must be after valid_from')
        return v


class ExtractedEntityContract(BaseModel):
    """Contract for extracted entity data."""
    
    name: str = Field(min_length=1)
    entity_type: EntityTypeContract
    confidence: float = Field(ge=0.0, le=1.0)
    context: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    temporal_info: TemporalInfoContract
    entity_uuid: Optional[str] = None


class ExtractedRelationshipContract(BaseModel):
    """Contract for extracted relationship data."""
    
    source_entity: str = Field(min_length=1)
    target_entity: str = Field(min_length=1) 
    relationship_type: RelationshipTypeContract
    confidence: float = Field(ge=0.0, le=1.0)
    context: str = ""
    evidence: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    temporal_info: TemporalInfoContract
    relationship_uuid: Optional[str] = None
    source_entity_uuid: Optional[str] = None
    target_entity_uuid: Optional[str] = None


# ============================================================================
# Database Layer Contracts
# ============================================================================

class QdrantPointContract(BaseModel):
    """Contract for QDrant point/document structure."""
    
    id: Union[str, int]
    vector: List[float] = Field(min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('vector')
    @classmethod
    def vector_not_empty(cls, v):
        if not v:
            raise ValueError('Vector cannot be empty')
        return v


class QdrantSearchRequestContract(BaseModel):
    """Contract for QDrant search requests."""
    
    collection_name: str = Field(min_length=1)
    query_vector: List[float] = Field(min_length=1)
    limit: int = Field(ge=1, le=1000, default=10)
    score_threshold: Optional[float] = Field(ge=0.0, le=1.0)
    filter_conditions: Optional[Dict[str, Any]] = None


class QdrantSearchResultContract(BaseModel):
    """Contract for QDrant search results."""
    
    id: Union[str, int]
    score: float = Field(ge=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    vector: Optional[List[float]] = None


class Neo4jNodeContract(BaseModel):
    """Contract for Neo4j node structure."""
    
    id: Union[str, int]
    labels: List[str] = Field(min_length=1)
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('labels')
    @classmethod
    def labels_not_empty(cls, v):
        if not v:
            raise ValueError('Node must have at least one label')
        return v


class Neo4jRelationshipContract(BaseModel):
    """Contract for Neo4j relationship structure."""
    
    id: Union[str, int]
    type: str = Field(min_length=1)
    start_node_id: Union[str, int]
    end_node_id: Union[str, int]
    properties: Dict[str, Any] = Field(default_factory=dict)


class DatabaseContract(BaseModel):
    """Generic database operation contract."""
    
    operation: str = Field(min_length=1)
    collection_name: str = Field(min_length=1)
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# AI/ML Service Contracts
# ============================================================================

class GraphitiExtractionRequestContract(BaseModel):
    """Contract for Graphiti entity extraction requests."""
    
    text: str = Field(min_length=1)
    document_id: Optional[str] = None
    extraction_config: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('text')
    @classmethod
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or whitespace only')
        return v


class GraphitiExtractionResultContract(BaseModel):
    """Contract for Graphiti entity extraction results."""
    
    entities: List[ExtractedEntityContract]
    relationships: List[ExtractedRelationshipContract] 
    processing_time: float = Field(ge=0.0)
    document_id: Optional[str] = None
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphitiStorageRequestContract(BaseModel):
    """Contract for Graphiti graph storage requests."""
    
    entities: List[ExtractedEntityContract]
    relationships: List[ExtractedRelationshipContract]
    transaction_id: Optional[str] = None
    storage_config: Dict[str, Any] = Field(default_factory=dict)


class GraphitiStorageResultContract(BaseModel):
    """Contract for Graphiti graph storage results."""
    
    stored_entities: int = Field(ge=0)
    stored_relationships: int = Field(ge=0)
    transaction_id: Optional[str] = None
    storage_time: float = Field(ge=0.0)
    errors: List[str] = Field(default_factory=list)


class GraphitiContract(BaseModel):
    """Main contract for Graphiti service interface."""
    
    extract_entities: GraphitiExtractionRequestContract
    storage_request: GraphitiStorageRequestContract
    expected_extraction_result: GraphitiExtractionResultContract
    expected_storage_result: GraphitiStorageResultContract


# ============================================================================
# Pipeline Contracts
# ============================================================================

class DocumentProcessingRequestContract(BaseModel):
    """Contract for document processing pipeline input."""
    
    document_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_options: Dict[str, Any] = Field(default_factory=dict)


class DocumentProcessingResultContract(BaseModel):
    """Contract for document processing pipeline output."""
    
    document_id: str
    qdrant_point_id: Union[str, int]
    neo4j_node_ids: List[Union[str, int]]
    entities_extracted: int = Field(ge=0)
    relationships_extracted: int = Field(ge=0)
    processing_time: float = Field(ge=0.0)
    status: str = Field(min_length=1)
    errors: List[str] = Field(default_factory=list)


class EmbeddingRequestContract(BaseModel):
    """Contract for embedding service requests."""
    
    text: str = Field(min_length=1)
    model_name: Optional[str] = None
    embedding_config: Dict[str, Any] = Field(default_factory=dict)


class EmbeddingResultContract(BaseModel):
    """Contract for embedding service results."""
    
    embedding: List[float] = Field(min_length=1)
    model_name: str = Field(min_length=1)
    dimensions: int = Field(ge=1)
    processing_time: float = Field(ge=0.0)


class PipelineContract(BaseModel):
    """Main contract for processing pipeline interface."""
    
    document_request: DocumentProcessingRequestContract
    embedding_request: EmbeddingRequestContract
    expected_document_result: DocumentProcessingResultContract
    expected_embedding_result: EmbeddingResultContract


# ============================================================================
# Data Synchronization Contracts
# ============================================================================

class IDMappingContract(BaseModel):
    """Contract for ID mapping between databases."""
    
    qdrant_id: Union[str, int]
    neo4j_id: Union[str, int]
    document_id: str = Field(min_length=1)
    mapping_type: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    status: str = Field(min_length=1)


class SyncEventContract(BaseModel):
    """Contract for synchronization events."""
    
    event_type: str = Field(min_length=1)  # CREATE, UPDATE, DELETE
    source_system: str = Field(min_length=1)  # qdrant, neo4j
    target_system: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    event_data: Dict[str, Any]
    timestamp: datetime
    event_id: str = Field(min_length=1)


class ConflictResolutionContract(BaseModel):
    """Contract for conflict resolution data."""
    
    conflict_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    conflict_type: str = Field(min_length=1)
    qdrant_version: Dict[str, Any]
    neo4j_version: Dict[str, Any]
    resolution_strategy: str = Field(min_length=1)
    resolved_version: Dict[str, Any]
    resolution_timestamp: datetime


class SyncContract(BaseModel):
    """Main contract for synchronization interface."""
    
    id_mapping: IDMappingContract
    sync_event: SyncEventContract
    conflict_resolution: ConflictResolutionContract


# ============================================================================
# External Service Contracts
# ============================================================================

class ConnectorAuthenticationContract(BaseModel):
    """Contract for connector authentication."""
    
    connector_type: str = Field(min_length=1)
    auth_method: str = Field(min_length=1)
    credentials: Dict[str, str]
    auth_url: Optional[str] = None
    token_expiry: Optional[datetime] = None


class ConnectorDataRequestContract(BaseModel):
    """Contract for connector data retrieval requests."""
    
    connector_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    query_parameters: Dict[str, Any] = Field(default_factory=dict)
    pagination: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None


class ConnectorDataResultContract(BaseModel):
    """Contract for connector data retrieval results."""
    
    connector_type: str
    source_id: str
    documents: List[Dict[str, Any]]
    total_count: int = Field(ge=0)
    fetched_count: int = Field(ge=0)
    has_more: bool = False
    next_cursor: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ServiceContract(BaseModel):
    """Main contract for external service interface."""
    
    authentication: ConnectorAuthenticationContract
    data_request: ConnectorDataRequestContract
    expected_data_result: ConnectorDataResultContract


# ============================================================================
# Search/Query Contracts
# ============================================================================

class HybridSearchRequestContract(BaseModel):
    """Contract for hybrid search requests."""
    
    query: str = Field(min_length=1)
    collection_name: str = Field(min_length=1)
    vector_weight: float = Field(ge=0.0, le=1.0, default=0.7)
    graph_weight: float = Field(ge=0.0, le=1.0, default=0.3)
    limit: int = Field(ge=1, le=100, default=10)
    filters: Optional[Dict[str, Any]] = None

    @field_validator('graph_weight')
    @classmethod
    def weights_sum_to_one(cls, v, info):
        if 'vector_weight' in info.data and abs((v + info.data['vector_weight']) - 1.0) > 0.001:
            raise ValueError('vector_weight and graph_weight must sum to 1.0')
        return v


class SearchResultItemContract(BaseModel):
    """Contract for individual search result items."""
    
    document_id: str = Field(min_length=1)
    content: str
    score: float = Field(ge=0.0, le=1.0)
    vector_score: float = Field(ge=0.0, le=1.0)
    graph_score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    related_entities: List[str] = Field(default_factory=list)


class HybridSearchResultContract(BaseModel):
    """Contract for hybrid search results."""
    
    query: str
    results: List[SearchResultItemContract]
    total_results: int = Field(ge=0)
    processing_time: float = Field(ge=0.0)
    vector_time: float = Field(ge=0.0)
    graph_time: float = Field(ge=0.0)
    fusion_time: float = Field(ge=0.0)


# ============================================================================
# Error Handling Contracts
# ============================================================================

class ErrorContract(BaseModel):
    """Contract for error responses."""
    
    error_code: str = Field(min_length=1)
    error_message: str = Field(min_length=1)
    error_type: str = Field(min_length=1)
    timestamp: datetime
    component: str = Field(min_length=1)
    details: Dict[str, Any] = Field(default_factory=dict)


class ValidationErrorContract(BaseModel):
    """Contract for validation errors."""
    
    field_name: str = Field(min_length=1)
    error_message: str = Field(min_length=1)
    invalid_value: Any
    expected_type: str = Field(min_length=1)
    validation_rule: str = Field(min_length=1) 