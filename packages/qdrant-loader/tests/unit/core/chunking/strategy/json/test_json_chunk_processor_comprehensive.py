"""Comprehensive tests for JSONChunkProcessor to achieve 80%+ coverage."""

from unittest.mock import Mock, patch

from qdrant_loader.core.chunking.strategy.json.json_chunk_processor import (
    JSONChunkProcessor,
)
from qdrant_loader.core.chunking.strategy.json.json_document_parser import (
    JSONElement,
    JSONElementType,
)
from qdrant_loader.core.document import Document


class TestJSONChunkProcessor:
    """Comprehensive tests for JSONChunkProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock settings with proper nested structure
        self.mock_settings = Mock()

        # Create nested mock structure
        mock_json_strategy = Mock()
        mock_json_strategy.max_chunk_size_for_nlp = 1000
        mock_json_strategy.enable_schema_inference = True

        mock_strategies = Mock()
        mock_strategies.json_strategy = mock_json_strategy

        mock_chunking = Mock()
        mock_chunking.strategies = mock_strategies
        mock_chunking.chunk_size = 1500

        mock_global_config = Mock()
        mock_global_config.chunking = mock_chunking

        self.mock_settings.global_config = mock_global_config

        # Create processor instance
        self.processor = JSONChunkProcessor(self.mock_settings)

        # Create test document
        self.test_doc = Document(
            content='{"test": "content"}',
            source="test_source",
            source_type="json",
            title="Test Document",
            url="https://test.com",
            content_type="application/json",
            metadata={"original": "metadata"},
        )
        self.test_doc.id = "test_doc_id"

    def test_init(self):
        """Test JSONChunkProcessor initialization."""
        assert self.processor.settings is self.mock_settings
        assert (
            self.processor.json_config
            is self.mock_settings.global_config.chunking.strategies.json_strategy
        )

    def test_create_chunk_document_basic(self):
        """Test basic chunk document creation."""
        chunk_content = '{"key": "value"}'
        chunk_metadata = {"test": "metadata"}

        with patch.object(
            self.processor, "_should_skip_nlp_for_json", return_value=False
        ):
            with patch.object(
                self.processor,
                "_create_enhanced_metadata",
                return_value={"enhanced": "metadata"},
            ):
                result = self.processor.create_chunk_document(
                    self.test_doc, chunk_content, 0, 5, chunk_metadata
                )

        assert isinstance(result, Document)
        assert result.content == chunk_content
        assert result.source == self.test_doc.source
        assert result.source_type == self.test_doc.source_type
        assert result.title == "Test Document_chunk_1"
        assert result.url == self.test_doc.url
        assert result.content_type == self.test_doc.content_type

    def test_create_chunk_document_with_skip_nlp(self):
        """Test chunk document creation with skip_nlp=True."""
        chunk_content = '{"large": "content"}'
        chunk_metadata = {"test": "metadata"}

        with patch.object(
            self.processor, "_should_skip_nlp_for_json", return_value=True
        ):
            with patch.object(
                self.processor,
                "_create_enhanced_metadata",
                return_value={"enhanced": "metadata"},
            ):
                result = self.processor.create_chunk_document(
                    self.test_doc, chunk_content, 2, 10, chunk_metadata, skip_nlp=True
                )

        assert isinstance(result, Document)
        assert result.title == "Test Document_chunk_3"

    def test_create_optimized_chunk_document(self):
        """Test optimized chunk document creation."""
        chunk_content = '{"optimized": "large content for optimization"}'

        with patch.object(
            self.processor,
            "_create_enhanced_metadata",
            return_value={"enhanced": "metadata"},
        ):
            result = self.processor.create_optimized_chunk_document(
                self.test_doc, chunk_content, 1, 3, skip_nlp=True
            )

        assert isinstance(result, Document)
        assert result.content == chunk_content
        assert result.title == "Test Document_chunk_2"
        assert isinstance(result, Document)

    def test_create_optimized_chunk_document_default_skip_nlp(self):
        """Test optimized chunk document with default skip_nlp=True."""
        chunk_content = '{"default": "optimization"}'

        with patch.object(
            self.processor,
            "_create_enhanced_metadata",
            return_value={"enhanced": "metadata"},
        ):
            result = self.processor.create_optimized_chunk_document(
                self.test_doc, chunk_content, 0, 1
            )

        assert isinstance(result, Document)

    def test_create_json_element_chunk_document(self):
        """Test chunk document creation from JSON element."""
        # Create mock JSON element
        element = Mock(spec=JSONElement)
        element.content = '{"element": "content"}'
        element.size = 500
        element.element_type = JSONElementType.OBJECT
        element.name = "test_element"
        element.path = "$.test_element"
        element.level = 2
        element.item_count = 5

        element_metadata = {"element_meta": "value"}

        with patch.object(
            self.processor,
            "_create_enhanced_metadata",
            return_value={"enhanced": "metadata"},
        ):
            result = self.processor.create_json_element_chunk_document(
                self.test_doc, element, 1, 4, element_metadata
            )

        assert isinstance(result, Document)
        assert result.content == element.content
        assert result.title == "Test Document_chunk_2"

    def test_create_json_element_chunk_document_large_element(self):
        """Test chunk document creation with large JSON element (skip NLP)."""
        element = Mock(spec=JSONElement)
        element.content = '{"large": "element content"}'
        element.size = 2000  # Larger than max_chunk_size_for_nlp (1000)
        element.element_type = JSONElementType.ARRAY
        element.name = "large_element"
        element.path = "$.large_element"
        element.level = 1
        element.item_count = 100

        with patch.object(
            self.processor,
            "_create_enhanced_metadata",
            return_value={"enhanced": "metadata"},
        ):
            result = self.processor.create_json_element_chunk_document(
                self.test_doc, element, 0, 2
            )

        assert isinstance(result, Document)

    def test_create_json_element_chunk_document_no_element_metadata(self):
        """Test chunk document creation without element metadata."""
        element = Mock(spec=JSONElement)
        element.content = '{"simple": "element"}'
        element.size = 200
        element.element_type = JSONElementType.VALUE
        element.name = "simple_element"
        element.path = "$.simple"
        element.level = 1
        element.item_count = 1

        with patch.object(
            self.processor,
            "_create_enhanced_metadata",
            return_value={"enhanced": "metadata"},
        ):
            result = self.processor.create_json_element_chunk_document(
                self.test_doc, element, 0, 1
            )

        assert isinstance(result, Document)

    def test_should_skip_nlp_for_json_large_content(self):
        """Test NLP skip decision for large content."""
        large_content = "x" * 2000  # Larger than max_chunk_size_for_nlp
        metadata = {}

        result = self.processor._should_skip_nlp_for_json(large_content, metadata)

        assert result is True

    def test_should_skip_nlp_for_json_data_types(self):
        """Test NLP skip decision for data container types."""
        content = '{"test": "content"}'
        metadata = {"json_type": "list", "structure_type": "primitive_collection"}

        result = self.processor._should_skip_nlp_for_json(content, metadata)

        assert result is True

    def test_should_skip_nlp_for_json_dict_configuration(self):
        """Test NLP skip decision for dict configuration type."""
        content = '{"config": "value"}'
        metadata = {"json_type": "dict", "structure_type": "configuration"}

        result = self.processor._should_skip_nlp_for_json(content, metadata)

        assert result is True

    def test_should_skip_nlp_for_json_minimal_text(self):
        """Test NLP skip decision for minimal text content."""
        content = '{"short": "text"}'
        metadata = {}

        with patch.object(
            self.processor, "_is_minimal_text_content", return_value=True
        ):
            result = self.processor._should_skip_nlp_for_json(content, metadata)

        assert result is True

    def test_should_skip_nlp_for_json_configuration_structure(self):
        """Test NLP skip decision for configuration structures."""
        content = '{"config": "structure"}'
        metadata = {}

        with patch.object(
            self.processor, "_is_minimal_text_content", return_value=False
        ):
            with patch.object(
                self.processor, "_is_configuration_structure", return_value=True
            ):
                result = self.processor._should_skip_nlp_for_json(content, metadata)

        assert result is True

    def test_should_skip_nlp_for_json_normal_content(self):
        """Test NLP skip decision for normal content (should not skip)."""
        content = (
            '{"description": "This is a long description with natural language text."}'
        )
        metadata = {"json_type": "object"}

        with patch.object(
            self.processor, "_is_minimal_text_content", return_value=False
        ):
            with patch.object(
                self.processor, "_is_configuration_structure", return_value=False
            ):
                result = self.processor._should_skip_nlp_for_json(content, metadata)

        assert result is False

    def test_is_minimal_text_content_with_minimal_text(self):
        """Test minimal text detection with mostly structural content."""
        content = '{"id": 123, "status": "active", "count": 456}'

        result = self.processor._is_minimal_text_content(content)

        assert result is True

    def test_is_minimal_text_content_with_rich_text(self):
        """Test minimal text detection with rich natural language content."""
        content = '{"description": "This is a comprehensive description with lots of natural language text that should be processed by NLP algorithms."}'

        result = self.processor._is_minimal_text_content(content)

        assert result is False

    def test_is_minimal_text_content_with_nested_text(self):
        """Test minimal text detection with nested structures containing text."""
        content = '{"user": {"bio": "Software engineer with passion for technology"}, "posts": [{"title": "Understanding JSON Processing", "content": "This article explains how JSON processing works in detail."}]}'

        result = self.processor._is_minimal_text_content(content)

        # Should return False because there's substantial text content
        assert result is False

    def test_is_minimal_text_content_invalid_json(self):
        """Test minimal text detection with invalid JSON."""
        content = "invalid json content"

        result = self.processor._is_minimal_text_content(content)

        assert result is False

    def test_is_configuration_structure_explicit_type(self):
        """Test configuration structure detection with explicit type."""
        metadata = {"structure_type": "configuration"}

        result = self.processor._is_configuration_structure(metadata)

        assert result is True

    def test_is_configuration_structure_multiple_indicators(self):
        """Test configuration structure detection with multiple indicators."""
        metadata = {"configuration_indicators": ["setting1", "setting2", "setting3"]}

        result = self.processor._is_configuration_structure(metadata)

        assert result is True

    def test_is_configuration_structure_schema_patterns(self):
        """Test configuration structure detection with schema patterns."""
        metadata = {"schema_patterns": ["configuration_object", "other_pattern"]}

        result = self.processor._is_configuration_structure(metadata)

        assert result is True

    def test_is_configuration_structure_feature_flags_pattern(self):
        """Test configuration structure detection with feature flags pattern."""
        metadata = {"schema_patterns": ["feature_flags"]}

        result = self.processor._is_configuration_structure(metadata)

        assert result is True

    def test_is_configuration_structure_typed_value_pattern(self):
        """Test configuration structure detection with typed value pattern."""
        metadata = {"schema_patterns": ["typed_value", "unrelated_pattern"]}

        result = self.processor._is_configuration_structure(metadata)

        assert result is True

    def test_is_configuration_structure_normal_content(self):
        """Test configuration structure detection with normal content."""
        metadata = {
            "structure_type": "normal",
            "configuration_indicators": ["single_indicator"],
            "schema_patterns": ["normal_pattern"],
        }

        result = self.processor._is_configuration_structure(metadata)

        assert result is False

    def test_create_enhanced_metadata(self):
        """Test enhanced metadata creation."""
        chunk_metadata = {
            "chunk_size": 500,
            "element_type": "object",
            "custom_field": "custom_value",
        }

        result = self.processor._create_enhanced_metadata(
            self.test_doc, chunk_metadata, 2, 5
        )

        # Should include original metadata
        assert result["original"] == "metadata"

        # Should include chunking information
        assert result["chunk_index"] == 2
        assert result["total_chunks"] == 5
        assert result["chunk_size"] == 500
        assert result["chunking_strategy"] == "json"
        assert result["is_chunk"] is True
        assert result["parent_document_id"] == "test_doc_id"

        # Should include JSON-specific metadata
        assert result["content_type"] == "json"
        assert result["json_processing_mode"] == "modular_architecture"
        assert (
            result["supports_schema_inference"]
            == self.processor.json_config.enable_schema_inference
        )

        # Should include custom chunk metadata
        assert result["custom_field"] == "custom_value"

        # Should include processing indicators
        assert result["processed_with_json_components"] is True
        assert result["json_config_version"] == "modular_v1"
        assert "chunk_quality_indicators" in result

    def test_calculate_chunk_quality_indicators_good_quality(self):
        """Test quality indicators calculation for good quality chunk."""
        chunk_metadata = {
            "chunk_size": 800,
            "element_type": "object",
            "is_valid_json": True,
            "nlp_skipped": False,
        }

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["size_appropriate"] is True
        assert result["structure_preserved"] is True
        assert result["schema_coherent"] is True
        assert result["nlp_suitable"] is True
        assert result["overall_quality_score"] == 1.0

    def test_calculate_chunk_quality_indicators_small_chunk(self):
        """Test quality indicators with small chunk size."""
        chunk_metadata = {"chunk_size": 50, "element_type": "object"}  # Too small

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["size_appropriate"] is False
        assert result["overall_quality_score"] < 1.0

    def test_calculate_chunk_quality_indicators_large_chunk(self):
        """Test quality indicators with large chunk size."""
        chunk_metadata = {
            "chunk_size": 4000,  # Too large (> 1500 * 2)
            "element_type": "object",
        }

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["size_appropriate"] is False

    def test_calculate_chunk_quality_indicators_grouped_elements(self):
        """Test quality indicators with grouped elements."""
        chunk_metadata = {"chunk_size": 800, "element_type": "grouped_elements"}

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["structure_preserved"] is False

    def test_calculate_chunk_quality_indicators_chunk_type(self):
        """Test quality indicators with chunk element type."""
        chunk_metadata = {"chunk_size": 800, "element_type": "chunk"}

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["structure_preserved"] is False

    def test_calculate_chunk_quality_indicators_invalid_json(self):
        """Test quality indicators with invalid JSON."""
        chunk_metadata = {
            "chunk_size": 800,
            "element_type": "object",
            "is_valid_json": False,
        }

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["schema_coherent"] is False

    def test_calculate_chunk_quality_indicators_nlp_skipped(self):
        """Test quality indicators with NLP skipped."""
        chunk_metadata = {
            "chunk_size": 800,
            "element_type": "object",
            "nlp_skipped": True,
        }

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["nlp_suitable"] is False

    def test_calculate_chunk_quality_indicators_multiple_issues(self):
        """Test quality indicators with multiple issues."""
        chunk_metadata = {
            "chunk_size": 50,  # Too small
            "element_type": "grouped_elements",  # Structure not preserved
            "is_valid_json": False,  # Invalid JSON
            "nlp_skipped": True,  # NLP skipped
        }

        result = self.processor._calculate_chunk_quality_indicators(chunk_metadata)

        assert result["size_appropriate"] is False
        assert result["structure_preserved"] is False
        assert result["schema_coherent"] is False
        assert result["nlp_suitable"] is False
        assert result["overall_quality_score"] == 0.0
