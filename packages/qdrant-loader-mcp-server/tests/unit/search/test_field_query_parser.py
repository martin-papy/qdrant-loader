"""Tests for FieldQueryParser component."""

import pytest
from qdrant_client.http import models
from qdrant_loader_mcp_server.search.components import (
    FieldQuery,
    FieldQueryParser,
)


class TestFieldQueryParser:
    """Test suite for FieldQueryParser."""

    @pytest.fixture
    def parser(self):
        """Create a FieldQueryParser instance."""
        return FieldQueryParser()

    def test_parse_simple_field_query(self, parser):
        """Test parsing a simple field query."""
        query = "source_type:confluence"
        parsed = parser.parse_query(query)

        assert len(parsed.field_queries) == 1
        assert parsed.field_queries[0].field_name == "source_type"
        assert parsed.field_queries[0].field_value == "confluence"
        assert parsed.text_query == ""

    def test_parse_multiple_field_queries(self, parser):
        """Test parsing multiple field queries."""
        query = "source_type:confluence project_id:my-project"
        parsed = parser.parse_query(query)

        assert len(parsed.field_queries) == 2
        assert parsed.field_queries[0].field_name == "source_type"
        assert parsed.field_queries[0].field_value == "confluence"
        assert parsed.field_queries[1].field_name == "project_id"
        assert parsed.field_queries[1].field_value == "my-project"
        assert parsed.text_query == ""

    def test_parse_field_query_with_text(self, parser):
        """Test parsing field query with remaining text search."""
        query = "source_type:confluence API documentation"
        parsed = parser.parse_query(query)

        assert len(parsed.field_queries) == 1
        assert parsed.field_queries[0].field_name == "source_type"
        assert parsed.text_query == "API documentation"

    def test_parse_quoted_field_value(self, parser):
        """Test parsing field query with quoted value."""
        query = 'title:"API Documentation"'
        parsed = parser.parse_query(query)

        assert len(parsed.field_queries) == 1
        assert parsed.field_queries[0].field_name == "title"
        assert parsed.field_queries[0].field_value == "API Documentation"

    def test_parse_nested_metadata_field(self, parser):
        """Test parsing nested metadata field queries."""
        query = "chunk_index:0 total_chunks:5"
        parsed = parser.parse_query(query)

        assert len(parsed.field_queries) == 2
        assert parsed.field_queries[0].field_name == "chunk_index"
        assert parsed.field_queries[0].field_value == "0"
        assert parsed.field_queries[1].field_name == "total_chunks"
        assert parsed.field_queries[1].field_value == "5"

    def test_create_filter_from_field_queries(self, parser):
        """Test creating Qdrant filter from field queries."""
        field_queries = [
            FieldQuery(
                field_name="source_type",
                field_value="confluence",
                original_query="source_type:confluence",
            ),
            FieldQuery(
                field_name="title", field_value="API", original_query="title:API"
            ),
        ]

        filter_obj = parser.create_qdrant_filter(field_queries)

        assert filter_obj is not None
        assert len(filter_obj.must) == 2
        assert filter_obj.must[0].key == "source_type"
        assert filter_obj.must[0].match.value == "confluence"
        assert filter_obj.must[1].key == "title"
        assert filter_obj.must[1].match.value == "API"

    def test_create_filter_with_nested_fields(self, parser):
        """Test creating Qdrant filter with nested metadata fields using dot notation."""
        field_queries = [
            FieldQuery(
                field_name="chunk_index",
                field_value="0",
                original_query="chunk_index:0",
            )
        ]

        filter_obj = parser.create_qdrant_filter(field_queries)

        assert filter_obj is not None
        assert len(filter_obj.must) == 1
        # Verify dot notation is used for nested fields
        assert filter_obj.must[0].key == "metadata.chunk_index"
        assert filter_obj.must[0].match.value == 0  # Should be converted to int

    def test_create_filter_with_project_ids(self, parser):
        """Test creating filter with project_ids in 3 locations."""
        project_ids = ["project-1", "project-2"]

        filter_obj = parser.create_qdrant_filter(
            field_queries=None, project_ids=project_ids
        )

        assert filter_obj is not None
        assert len(filter_obj.must) == 1
        # Should be a nested Filter with should clause
        nested_filter = filter_obj.must[0]
        assert isinstance(nested_filter, models.Filter)
        assert len(nested_filter.should) == 3
        # Check all 3 locations
        assert nested_filter.should[0].key == "project_id"
        assert nested_filter.should[1].key == "source"
        assert nested_filter.should[2].key == "metadata.project_id"

    def test_create_filter_field_queries_and_project_ids(self, parser):
        """Test creating filter with both field queries and project_ids."""
        field_queries = [
            FieldQuery(
                field_name="source_type",
                field_value="confluence",
                original_query="source_type:confluence",
            )
        ]
        project_ids = ["my-project"]

        filter_obj = parser.create_qdrant_filter(field_queries, project_ids)

        assert filter_obj is not None
        assert len(filter_obj.must) == 2
        # First condition: field query
        assert filter_obj.must[0].key == "source_type"
        # Second condition: project filter (nested Filter with should)
        assert isinstance(filter_obj.must[1], models.Filter)
        assert len(filter_obj.must[1].should) == 3

    def test_skip_project_filter_when_field_query_has_project_id(self, parser):
        """Test that project filter is skipped when field query contains project_id."""
        field_queries = [
            FieldQuery(
                field_name="project_id",
                field_value="specific-project",
                original_query="project_id:specific-project",
            )
        ]
        project_ids = ["my-project"]

        filter_obj = parser.create_qdrant_filter(field_queries, project_ids)

        assert filter_obj is not None
        # Should only have the field query, not the project filter
        assert len(filter_obj.must) == 1
        assert filter_obj.must[0].key == "project_id"
        assert filter_obj.must[0].match.value == "specific-project"

    def test_numeric_field_conversion(self, parser):
        """Test that numeric fields are converted to int."""
        field_queries = [
            FieldQuery(
                field_name="chunk_index",
                field_value="42",
                original_query="chunk_index:42",
            ),
            FieldQuery(
                field_name="total_chunks",
                field_value="100",
                original_query="total_chunks:100",
            ),
        ]

        filter_obj = parser.create_qdrant_filter(field_queries)

        assert filter_obj is not None
        assert filter_obj.must[0].match.value == 42  # int, not string
        assert filter_obj.must[1].match.value == 100  # int, not string

    def test_should_use_filter_only_with_document_id(self, parser):
        """Test filter-only mode for document_id queries."""
        parsed = parser.parse_query("document_id:abc123 some text")

        # Even with text, document_id queries should be filter-only
        assert parser.should_use_filter_only(parsed) is True

    def test_should_use_filter_only_without_text(self, parser):
        """Test filter-only mode when no text search."""
        parsed = parser.parse_query("source_type:confluence")

        assert parser.should_use_filter_only(parsed) is True

    def test_should_not_use_filter_only_with_text(self, parser):
        """Test that filter-only is False when text search is present."""
        parsed = parser.parse_query("source_type:confluence API documentation")

        # Should use both filter and text search
        assert parser.should_use_filter_only(parsed) is False

    def test_empty_query(self, parser):
        """Test handling empty query."""
        parsed = parser.parse_query("")

        assert len(parsed.field_queries) == 0
        assert parsed.text_query == ""
        assert parser.create_qdrant_filter(parsed.field_queries) is None

    def test_unsupported_field(self, parser):
        """Test handling unsupported field."""
        query = "invalid_field:value regular text"
        parsed = parser.parse_query(query)

        # Unsupported field should be treated as regular text
        assert len(parsed.field_queries) == 0
        # The entire query becomes text search since field is unsupported
        assert "invalid_field:value" in parsed.text_query
        assert "regular text" in parsed.text_query

    def test_get_supported_fields(self, parser):
        """Test getting list of supported fields."""
        fields = parser.get_supported_fields()

        assert "document_id" in fields
        assert "source_type" in fields
        assert "project_id" in fields
        assert "chunk_index" in fields
        assert (
            "metadata.chunk_index" not in fields
        )  # Should be chunk_index, not the payload key
