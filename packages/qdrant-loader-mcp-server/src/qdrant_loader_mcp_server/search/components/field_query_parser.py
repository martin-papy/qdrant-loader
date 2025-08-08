"""Field query parser for handling field-specific search syntax."""

import re
from typing import Any, Optional, Tuple
from dataclasses import dataclass

from qdrant_client.http import models

from ...utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class FieldQuery:
    """Represents a parsed field query."""
    field_name: str
    field_value: str
    original_query: str
    remaining_query: str = ""  # Any remaining text after field extraction


@dataclass
class ParsedQuery:
    """Represents a fully parsed query with field filters and text search."""
    field_queries: list[FieldQuery]
    text_query: str
    original_query: str


class FieldQueryParser:
    """Parses field-specific query syntax and converts to Qdrant filters."""
    
    # Supported field mappings (field_name -> qdrant_payload_key)
    SUPPORTED_FIELDS = {
        "document_id": "document_id",
        "source_type": "source_type", 
        "source": "source",
        "project_id": "project_id",
        "title": "title",
        "url": "url",
        "file_path": "file_path",
        "file_name": "file_name",
        "file_type": "file_type",
        "collection_name": "collection_name",
        # Nested metadata fields
        "chunk_index": "metadata.chunk_index",
        "total_chunks": "metadata.total_chunks",
        "chunking_strategy": "metadata.chunking_strategy",
        "original_file_type": "metadata.original_file_type",
        "conversion_method": "metadata.conversion_method",
    }
    
    # Field query pattern: field_name:value or field_name:"quoted value"
    FIELD_PATTERN = re.compile(r'(\w+):(?:"([^"]+)"|([^\s]+))')
    
    def __init__(self):
        """Initialize the field query parser."""
        self.logger = LoggingConfig.get_logger(__name__)
    
    def parse_query(self, query: str) -> ParsedQuery:
        """Parse a query string into field queries and text search.
        
        Args:
            query: The input query string
            
        Returns:
            ParsedQuery object with separated field queries and text search
            
        Examples:
            "document_id:abc123" -> field_queries=[FieldQuery(field_name="document_id", field_value="abc123")]
            "document_id:abc123 python tutorial" -> field + text search
            "source_type:confluence title:\"API Documentation\"" -> multiple field queries
        """
        field_queries = []
        remaining_text = query

        # Find all field:value patterns and collect spans to remove safely
        matches = list(self.FIELD_PATTERN.finditer(query))
        spans_to_remove: list[tuple[int, int]] = []

        for match in matches:
            field_name = match.group(1)
            field_value = match.group(2) or match.group(3)  # quoted or unquoted value

            if field_name in self.SUPPORTED_FIELDS:
                field_query = FieldQuery(
                    field_name=field_name,
                    field_value=field_value,
                    original_query=match.group(0)
                )
                field_queries.append(field_query)
                spans_to_remove.append(match.span())
                self.logger.debug(f"Parsed field query: {field_name}={field_value}")
            else:
                self.logger.warning(f"Unsupported field: {field_name}")

        # Remove matched substrings from remaining_text by slicing in reverse order
        if spans_to_remove:
            parts = []
            last_index = len(query)
            for start, end in sorted(spans_to_remove, key=lambda s: s[0], reverse=True):
                # Append segment after this match
                parts.append(query[end:last_index])
                last_index = start
            parts.append(query[:last_index])
            remaining_text = "".join(reversed(parts)).strip()
        
        # Clean up remaining text (remove extra spaces)
        text_query = re.sub(r'\s+', ' ', remaining_text).strip()
        
        parsed = ParsedQuery(
            field_queries=field_queries,
            text_query=text_query,
            original_query=query
        )
        
        self.logger.debug(f"Parsed query: {len(field_queries)} field queries, text: '{text_query}'")
        return parsed
    
    def create_qdrant_filter(self, field_queries: list[FieldQuery] | None, project_ids: list[str] | None = None) -> models.Filter | None:
        """Create a Qdrant filter from field queries.
        
        Args:
            field_queries: List of field queries to convert to filters
            project_ids: Optional project ID filters to include
            
        Returns:
            Qdrant Filter object or None if no filters needed
        """
        must_conditions = []
        
        # Add field query conditions
        if field_queries:
            for field_query in field_queries:
                payload_key = self.SUPPORTED_FIELDS[field_query.field_name]
                
                # Handle nested fields (e.g., metadata.chunk_index)
                if "." in payload_key:
                    # For nested fields, use nested condition
                    parts = payload_key.split(".", 1)
                    condition = models.NestedCondition(
                        nested=models.Nested(
                            key=parts[0],
                            filter=models.Filter(
                                must=[
                                    models.FieldCondition(
                                        key=parts[1],
                                        match=models.MatchValue(value=field_query.field_value)
                                    )
                                ]
                            )
                        )
                    )
                else:
                    # For top-level fields, use direct field condition
                    condition = models.FieldCondition(
                        key=payload_key,
                        match=models.MatchValue(value=field_query.field_value)
                    )
                
                must_conditions.append(condition)
                self.logger.debug(f"Added filter condition: {payload_key} = {field_query.field_value}")
        
        # Add project ID filters if provided
        if project_ids:
            project_condition = models.FieldCondition(
                key="project_id", 
                match=models.MatchAny(any=project_ids)
            )
            must_conditions.append(project_condition)
            self.logger.debug(f"Added project filter: {project_ids}")
        
        # Return filter if we have conditions
        if must_conditions:
            return models.Filter(must=must_conditions)
        
        return None
    
    def should_use_filter_only(self, parsed_query: ParsedQuery) -> bool:
        """Determine if we should use filter-only search (no text search).
        
        Args:
            parsed_query: The parsed query object
            
        Returns:
            True if this should be a filter-only search (exact field matching)
        """
        # Use filter-only if we have field queries but no meaningful text search
        has_field_queries = len(parsed_query.field_queries) > 0
        has_meaningful_text = len(parsed_query.text_query.strip()) > 0
        
        # Special case: document_id queries should be exact matches
        has_document_id_query = any(
            fq.field_name == "document_id" for fq in parsed_query.field_queries
        )
        
        return has_field_queries and (not has_meaningful_text or has_document_id_query)
    
    def get_supported_fields(self) -> list[str]:
        """Get list of supported field names for queries.
        
        Returns:
            List of supported field names
        """
        return list(self.SUPPORTED_FIELDS.keys())