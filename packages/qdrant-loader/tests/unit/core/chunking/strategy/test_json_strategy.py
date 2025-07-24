"""Unit tests for JSON chunking strategy."""

import json
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.config.types import SourceType
from qdrant_loader.core.chunking.strategy.json_strategy import (
    MAX_ARRAY_ITEMS_TO_PROCESS,
    MAX_JSON_SIZE_FOR_PARSING,
    MAX_OBJECT_KEYS_TO_PROCESS,
    MAX_OBJECTS_TO_PROCESS,
    MAX_RECURSION_DEPTH,
    SIMPLE_CHUNKING_THRESHOLD,
    JSONChunkingStrategy,
    JSONElement,
    JSONElementType,
)
from qdrant_loader.core.document import Document


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)

    # Mock global_config
    global_config = Mock()

    # Mock chunking config
    chunking_config = Mock()
    chunking_config.chunk_size = 1000
    chunking_config.chunk_overlap = 100

    # Mock semantic analysis config
    semantic_analysis_config = Mock()
    semantic_analysis_config.num_topics = 5
    semantic_analysis_config.lda_passes = 10
    semantic_analysis_config.spacy_model = "en_core_web_sm"
    
    # Mock embedding config
    embedding_config = Mock()
    embedding_config.tokenizer = "cl100k_base"

    global_config.chunking = chunking_config
    global_config.semantic_analysis = semantic_analysis_config
    global_config.embedding = embedding_config
    settings.global_config = global_config

    return settings


@pytest.fixture
def json_strategy(mock_settings):
    """Create a JSON chunking strategy instance."""
    with (
        patch("qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer"),
        patch("spacy.load") as mock_spacy_load,
    ):
        # Setup spacy mock
        mock_nlp = Mock()
        mock_nlp.pipe_names = []
        mock_spacy_load.return_value = mock_nlp
        
        return JSONChunkingStrategy(mock_settings)


@pytest.fixture
def sample_json_document():
    """Create a sample JSON document for testing."""
    json_content = """
    {
        "users": [
            {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "profile": {
                    "age": 30,
                    "city": "New York"
                }
            },
            {
                "id": 2,
                "name": "Jane Smith",
                "email": "jane@example.com",
                "profile": {
                    "age": 25,
                    "city": "Los Angeles"
                }
            }
        ],
        "metadata": {
            "version": "1.0",
            "created": "2023-01-01",
            "total_users": 2
        }
    }
    """

    return Document(
        content=json_content.strip(),
        metadata={"file_name": "users.json"},
        source="test_source",
        source_type=SourceType.LOCALFILE,
        url="file://test_source",
        title="Test JSON Document",
        content_type="json",
    )


class TestJSONElement:
    """Test cases for JSONElement dataclass."""

    def test_json_element_creation(self):
        """Test JSONElement creation and basic properties."""
        element = JSONElement(
            name="test",
            element_type=JSONElementType.OBJECT,
            content='{"key": "value"}',
            value={"key": "value"},
            path="root.test",
            level=1,
            size=15,
            item_count=1,
        )

        assert element.name == "test"
        assert element.element_type == JSONElementType.OBJECT
        assert element.content == '{"key": "value"}'
        assert element.value == {"key": "value"}
        assert element.path == "root.test"
        assert element.level == 1
        assert element.size == 15
        assert element.item_count == 1
        assert element.parent is None
        assert element.children == []

    def test_add_child(self):
        """Test adding child elements."""
        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.OBJECT,
            content="{}",
            value={},
            path="root.parent",
            level=0,
        )

        child = JSONElement(
            name="child",
            element_type=JSONElementType.PROPERTY,
            content='"value"',
            value="value",
            path="root.parent.child",
            level=1,
        )

        parent.add_child(child)

        assert len(parent.children) == 1
        assert parent.children[0] == child
        assert child.parent == parent


class TestJSONElementType:
    """Test cases for JSONElementType enum."""

    def test_element_types(self):
        """Test all element types are available."""
        assert JSONElementType.OBJECT.value == "object"
        assert JSONElementType.ARRAY.value == "array"
        assert JSONElementType.ARRAY_ITEM.value == "array_item"
        assert JSONElementType.PROPERTY.value == "property"
        assert JSONElementType.VALUE.value == "value"
        assert JSONElementType.ROOT.value == "root"


class TestJSONChunkingStrategy:
    """Test cases for JSON chunking strategy."""

    def test_initialization(self, json_strategy):
        """Test that the strategy initializes correctly."""
        assert json_strategy is not None
        assert json_strategy.min_chunk_size == 200
        assert json_strategy.max_array_items_per_chunk == 50

    def test_parse_json_structure(self, json_strategy, sample_json_document):
        """Test JSON structure parsing."""
        root_element = json_strategy._parse_json_structure(sample_json_document.content)

        assert root_element is not None
        assert root_element.name == "root"
        assert root_element.element_type == JSONElementType.ROOT
        assert len(root_element.children) == 2  # users and metadata

    def test_parse_json_structure_too_large(self, json_strategy):
        """Test parsing very large JSON files."""
        large_content = "x" * (MAX_JSON_SIZE_FOR_PARSING + 1)

        result = json_strategy._parse_json_structure(large_content)

        assert result is None

    def test_parse_json_structure_invalid_json(self, json_strategy):
        """Test parsing invalid JSON."""
        invalid_content = '{"invalid": json content}'

        result = json_strategy._parse_json_structure(invalid_content)

        assert result is None

    def test_parse_json_structure_exception(self, json_strategy):
        """Test parsing with general exception."""
        with patch("json.loads", side_effect=Exception("Test error")):
            result = json_strategy._parse_json_structure('{"valid": "json"}')

            assert result is None

    def test_create_json_element_dict(self, json_strategy):
        """Test creating JSON element from dictionary."""
        value = {"key1": "value1", "key2": "value2"}

        element = json_strategy._create_json_element(
            "test_dict", value, JSONElementType.OBJECT, "root.test_dict", 1
        )

        assert element.name == "test_dict"
        assert element.element_type == JSONElementType.OBJECT
        assert element.value == value
        assert element.path == "root.test_dict"
        assert element.level == 1
        assert element.item_count == 2
        assert element.size > 0

    def test_create_json_element_list(self, json_strategy):
        """Test creating JSON element from list."""
        value = ["item1", "item2", "item3"]

        element = json_strategy._create_json_element(
            "test_list", value, JSONElementType.ARRAY, "root.test_list", 1
        )

        assert element.name == "test_list"
        assert element.element_type == JSONElementType.ARRAY
        assert element.value == value
        assert element.path == "root.test_list"
        assert element.level == 1
        assert element.item_count == 3
        assert element.size > 0

    def test_create_json_element_simple_value(self, json_strategy):
        """Test creating JSON element from simple value."""
        value = "simple_string"

        element = json_strategy._create_json_element(
            "test_string", value, JSONElementType.PROPERTY, "root.test_string", 1
        )

        assert element.name == "test_string"
        assert element.element_type == JSONElementType.PROPERTY
        assert element.value == value
        assert element.path == "root.test_string"
        assert element.level == 1
        assert element.item_count == 0
        assert element.size > 0

    def test_create_json_element_json_error(self, json_strategy):
        """Test creating JSON element with JSON serialization error."""

        # Create an object that can't be JSON serialized
        class UnserializableObject:
            pass

        value = UnserializableObject()

        element = json_strategy._create_json_element(
            "test_unserializable", value, JSONElementType.OBJECT, "root.test", 1
        )

        assert element.name == "test_unserializable"
        assert element.content == str(value)

    def test_extract_json_elements_dict(self, json_strategy):
        """Test extracting elements from dictionary."""
        data = {
            "simple_key": "simple_value",
            "complex_key": {"nested": "value"},
            "array_key": [1, 2, 3],
        }

        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.ROOT,
            content="",
            value=data,
            path="root",
        )

        json_strategy._extract_json_elements(parent, data, "root", 0)

        assert len(parent.children) == 3

        # Check simple property
        simple_child = next(c for c in parent.children if c.name == "simple_key")
        assert simple_child.element_type == JSONElementType.PROPERTY
        assert simple_child.value == "simple_value"

        # Check complex object
        complex_child = next(c for c in parent.children if c.name == "complex_key")
        assert complex_child.element_type == JSONElementType.OBJECT
        assert complex_child.value == {"nested": "value"}

        # Check array
        array_child = next(c for c in parent.children if c.name == "array_key")
        assert array_child.element_type == JSONElementType.ARRAY
        assert array_child.value == [1, 2, 3]

    def test_extract_json_elements_list(self, json_strategy):
        """Test extracting elements from list."""
        data = ["simple_item", {"complex": "item"}, [1, 2, 3]]

        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.ROOT,
            content="",
            value=data,
            path="root",
        )

        json_strategy._extract_json_elements(parent, data, "root", 0)

        assert len(parent.children) == 3

        # Check simple array item
        simple_child = parent.children[0]
        assert simple_child.name == "item_0"
        assert simple_child.element_type == JSONElementType.ARRAY_ITEM
        assert simple_child.value == "simple_item"

        # Check complex object in array
        complex_child = parent.children[1]
        assert complex_child.name == "item_1"
        assert complex_child.element_type == JSONElementType.OBJECT
        assert complex_child.value == {"complex": "item"}

        # Check nested array
        array_child = parent.children[2]
        assert array_child.name == "item_2"
        assert array_child.element_type == JSONElementType.ARRAY
        assert array_child.value == [1, 2, 3]

    def test_extract_json_elements_recursion_limit(self, json_strategy):
        """Test recursion depth limit."""
        # Create deeply nested structure
        data: dict = {"level": 0}
        current: dict = data
        for i in range(MAX_RECURSION_DEPTH + 2):
            nested_dict: dict = {"level": i + 1}
            current["nested"] = nested_dict
            current = nested_dict

        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.ROOT,
            content="",
            value=data,
            path="root",
        )

        json_strategy._extract_json_elements(parent, data, "root", 0)

        # Should have both "level" and "nested" children at the top level
        # The recursion limit applies to deeper levels
        assert len(parent.children) == 2  # level and nested

    def test_extract_json_elements_object_limit(self, json_strategy):
        """Test object processing limit."""
        # Create object with many keys
        data = {
            f"key_{i}": f"value_{i}" for i in range(MAX_OBJECT_KEYS_TO_PROCESS + 10)
        }

        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.ROOT,
            content="",
            value=data,
            path="root",
        )

        json_strategy._extract_json_elements(parent, data, "root", 0)

        # Should be limited to MAX_OBJECT_KEYS_TO_PROCESS
        assert len(parent.children) <= MAX_OBJECT_KEYS_TO_PROCESS

    def test_extract_json_elements_array_limit(self, json_strategy):
        """Test array processing limit."""
        # Create large array
        data = [f"item_{i}" for i in range(MAX_ARRAY_ITEMS_TO_PROCESS + 10)]

        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.ROOT,
            content="",
            value=data,
            path="root",
        )

        json_strategy._extract_json_elements(parent, data, "root", 0)

        # Should be limited to MAX_ARRAY_ITEMS_TO_PROCESS
        assert len(parent.children) <= MAX_ARRAY_ITEMS_TO_PROCESS

    def test_extract_json_elements_global_limit(self, json_strategy):
        """Test global object processing limit."""
        # Create structure that would exceed global limit
        data = {}
        for i in range(MAX_OBJECTS_TO_PROCESS + 10):
            data[f"key_{i}"] = {"nested": f"value_{i}"}

        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.ROOT,
            content="",
            value=data,
            path="root",
        )

        processed_count = [0]
        json_strategy._extract_json_elements(parent, data, "root", 0, processed_count)

        # Should respect global limit
        assert processed_count[0] <= MAX_OBJECTS_TO_PROCESS

    def test_group_small_elements_empty(self, json_strategy):
        """Test grouping empty list of elements."""
        result = json_strategy._group_small_elements([])

        assert result == []

    def test_group_small_elements_large_elements(self, json_strategy):
        """Test grouping with large elements that should remain separate."""
        large_element = JSONElement(
            name="large",
            element_type=JSONElementType.OBJECT,
            content="x" * 500,
            value={},
            path="root.large",
            size=500,
            item_count=1,
        )

        result = json_strategy._group_small_elements([large_element])

        assert len(result) == 1
        assert result[0] == large_element

    def test_group_small_elements_small_elements(self, json_strategy):
        """Test grouping small elements together."""
        small_elements = []
        for i in range(3):
            element = JSONElement(
                name=f"small_{i}",
                element_type=JSONElementType.PROPERTY,
                content=f"value_{i}",
                value=f"value_{i}",
                path=f"root.small_{i}",
                size=10,
                item_count=0,
            )
            small_elements.append(element)

        result = json_strategy._group_small_elements(small_elements)

        # Should group small elements
        assert len(result) == 1
        assert result[0].name.startswith("grouped_elements_")

    def test_group_small_elements_mixed(self, json_strategy):
        """Test grouping mixed small and large elements."""
        small_element = JSONElement(
            name="small",
            element_type=JSONElementType.PROPERTY,
            content="small",
            value="small",
            path="root.small",
            size=10,
            item_count=0,
        )

        large_element = JSONElement(
            name="large",
            element_type=JSONElementType.OBJECT,
            content="x" * 500,
            value={},
            path="root.large",
            size=500,
            item_count=1,
        )

        result = json_strategy._group_small_elements([small_element, large_element])

        # Should have grouped small element and separate large element
        assert len(result) == 2

    def test_group_small_elements_size_threshold(self, json_strategy):
        """Test grouping elements that reach size threshold."""
        elements = []
        for i in range(5):
            element = JSONElement(
                name=f"element_{i}",
                element_type=JSONElementType.PROPERTY,
                content="x" * 50,
                value=f"value_{i}",
                path=f"root.element_{i}",
                size=50,
                item_count=0,
            )
            elements.append(element)

        result = json_strategy._group_small_elements(elements)

        # Should create multiple groups based on size threshold
        assert len(result) >= 1

    def test_create_grouped_element_empty_list(self, json_strategy):
        """Test creating grouped element from empty list."""
        with pytest.raises(ValueError, match="Cannot group empty list of elements"):
            json_strategy._create_grouped_element([])

    def test_create_grouped_element_single_element(self, json_strategy):
        """Test creating grouped element from single element."""
        element = JSONElement(
            name="single",
            element_type=JSONElementType.PROPERTY,
            content="value",
            value="value",
            path="root.single",
        )

        result = json_strategy._create_grouped_element([element])

        assert result == element

    def test_create_grouped_element_array_items(self, json_strategy):
        """Test creating grouped element from array items."""
        elements = []
        for i in range(3):
            element = JSONElement(
                name=f"item_{i}",
                element_type=JSONElementType.ARRAY_ITEM,
                content=f'"value_{i}"',
                value=f"value_{i}",
                path=f"root[{i}]",
            )
            elements.append(element)

        result = json_strategy._create_grouped_element(elements)

        assert result.element_type == JSONElementType.ARRAY
        assert result.name == "grouped_items_3"
        assert result.value == ["value_0", "value_1", "value_2"]

    def test_create_grouped_element_mixed_elements(self, json_strategy):
        """Test creating grouped element from mixed elements."""
        elements = [
            JSONElement(
                name="prop1",
                element_type=JSONElementType.PROPERTY,
                content='"value1"',
                value="value1",
                path="root.prop1",
            ),
            JSONElement(
                name="prop2",
                element_type=JSONElementType.PROPERTY,
                content='"value2"',
                value="value2",
                path="root.prop2",
            ),
        ]

        result = json_strategy._create_grouped_element(elements)

        assert result.element_type == JSONElementType.OBJECT
        assert result.name == "grouped_elements_2"
        assert result.value == {"prop1": "value1", "prop2": "value2"}

    def test_create_grouped_element_root_name_handling(self, json_strategy):
        """Test creating grouped element with root name handling."""
        element = JSONElement(
            name="root",
            element_type=JSONElementType.PROPERTY,
            content='"value"',
            value="value",
            path="root",
        )

        result = json_strategy._create_grouped_element([element])

        assert result == element

    def test_split_large_element_small_element(self, json_strategy):
        """Test splitting element that's already small enough."""
        small_element = JSONElement(
            name="small",
            element_type=JSONElementType.OBJECT,
            content="small",
            value={},
            path="root.small",
            size=10,
        )

        result = json_strategy._split_large_element(small_element)

        assert len(result) == 1
        assert result[0] == small_element

    def test_split_large_element_array(self, json_strategy):
        """Test splitting large array element."""
        large_array = list(range(100))  # Large array
        large_element = JSONElement(
            name="large_array",
            element_type=JSONElementType.ARRAY,
            content=json.dumps(large_array),
            value=large_array,
            path="root.large_array",
            size=len(json.dumps(large_array)),
        )

        # Set chunk size to force splitting
        json_strategy.chunk_size = 100

        result = json_strategy._split_large_element(large_element)

        # Should split into multiple chunks
        assert len(result) > 1
        for chunk in result:
            assert chunk.element_type == JSONElementType.ARRAY
            assert chunk.name.startswith("large_array_chunk_")

    def test_split_large_element_object(self, json_strategy):
        """Test splitting large object element."""
        large_object = {f"key_{i}": f"value_{i}" for i in range(100)}
        large_element = JSONElement(
            name="large_object",
            element_type=JSONElementType.OBJECT,
            content=json.dumps(large_object),
            value=large_object,
            path="root.large_object",
            size=len(json.dumps(large_object)),
        )

        # Set chunk size to force splitting
        json_strategy.chunk_size = 100

        result = json_strategy._split_large_element(large_element)

        # Should split into multiple chunks
        assert len(result) > 1
        for chunk in result:
            assert chunk.element_type == JSONElementType.OBJECT
            assert chunk.name.startswith("large_object_chunk_")

    def test_split_large_element_text_fallback(self, json_strategy):
        """Test splitting large element with text fallback."""
        large_content = "\n".join([f"line_{i}" for i in range(100)])
        large_element = JSONElement(
            name="large_text",
            element_type=JSONElementType.VALUE,
            content=large_content,
            value=large_content,
            path="root.large_text",
            size=len(large_content),
        )

        # Set chunk size to force splitting
        json_strategy.chunk_size = 100

        result = json_strategy._split_large_element(large_element)

        # Should split into multiple chunks
        assert len(result) > 1
        for chunk in result:
            assert chunk.name.startswith("large_text_chunk_")

    def test_extract_json_metadata_object(self, json_strategy):
        """Test extracting metadata from object element."""
        element = JSONElement(
            name="test_object",
            element_type=JSONElementType.OBJECT,
            content='{"key": "value", "nested": {"inner": "value"}}',
            value={"key": "value", "nested": {"inner": "value"}},
            path="root.test_object",
            level=1,
            size=50,
            item_count=2,
        )

        metadata = json_strategy._extract_json_metadata(element)

        assert metadata["element_type"] == "object"
        assert metadata["name"] == "test_object"
        assert metadata["path"] == "root.test_object"
        assert metadata["level"] == 1
        assert metadata["size"] == 50
        assert metadata["item_count"] == 2
        assert metadata["has_nested_objects"] is True
        assert "str" in metadata["data_types"]

    def test_extract_json_metadata_array(self, json_strategy):
        """Test extracting metadata from array element."""
        element = JSONElement(
            name="test_array",
            element_type=JSONElementType.ARRAY,
            content='[1, "string", {"object": "value"}]',
            value=[1, "string", {"object": "value"}],
            path="root.test_array",
            level=1,
            size=40,
            item_count=3,
        )

        metadata = json_strategy._extract_json_metadata(element)

        assert metadata["element_type"] == "array"
        assert metadata["has_nested_objects"] is True
        assert metadata["has_arrays"] is False
        assert "int" in metadata["data_types"]
        assert "str" in metadata["data_types"]
        assert "dict" in metadata["data_types"]

    def test_extract_json_metadata_with_parent(self, json_strategy):
        """Test extracting metadata with parent context."""
        parent = JSONElement(
            name="parent",
            element_type=JSONElementType.ROOT,
            content="",
            value={},
            path="root",
        )

        child = JSONElement(
            name="child",
            element_type=JSONElementType.PROPERTY,
            content='"value"',
            value="value",
            path="root.child",
            parent=parent,
        )

        metadata = json_strategy._extract_json_metadata(child)

        assert metadata["parent_name"] == "parent"
        assert metadata["parent_type"] == "root"
        assert metadata["parent_path"] == "root"

    def test_extract_json_metadata_simple_value(self, json_strategy):
        """Test extracting metadata from simple value."""
        element = JSONElement(
            name="simple",
            element_type=JSONElementType.PROPERTY,
            content='"simple_value"',
            value="simple_value",
            path="root.simple",
        )

        metadata = json_strategy._extract_json_metadata(element)

        assert metadata["data_types"] == ["str"]
        assert metadata["has_nested_objects"] is False
        assert metadata["has_arrays"] is False

    def test_chunk_document(self, json_strategy, sample_json_document):
        """Test document chunking."""
        chunks = json_strategy.chunk_document(sample_json_document)

        assert len(chunks) > 0
        assert all(isinstance(chunk, Document) for chunk in chunks)

        # Check that chunks have proper metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert chunk.metadata["parent_document_id"] == sample_json_document.id
            assert "element_type" in chunk.metadata
            assert "chunking_method" in chunk.metadata

    def test_chunk_document_large_file_fallback(self, json_strategy):
        """Test chunking very large JSON files that trigger fallback."""
        # Create content larger than SIMPLE_CHUNKING_THRESHOLD
        large_content = '{"data": "' + "x" * SIMPLE_CHUNKING_THRESHOLD + '"}'

        large_doc = Document(
            content=large_content,
            metadata={"file_name": "large.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Large JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(large_doc)

        assert len(chunks) > 0
        # Should use simple chunking
        assert chunks[0].metadata.get("chunking_method") == "fallback_text"

    def test_chunk_document_parsing_failure(self, json_strategy):
        """Test chunking when JSON parsing fails."""
        with patch.object(json_strategy, "_parse_json_structure", return_value=None):
            doc = Document(
                content='{"valid": "json"}',
                metadata={"file_name": "test.json"},
                source="test_source",
                source_type=SourceType.LOCALFILE,
                url="file://test_source",
                title="Test JSON",
                content_type="json",
            )

            chunks = json_strategy.chunk_document(doc)

            assert len(chunks) > 0
            assert chunks[0].metadata.get("chunking_method") == "fallback_text"

    def test_chunk_document_no_children(self, json_strategy):
        """Test chunking when root element has no children."""
        simple_doc = Document(
            content='"simple_string"',
            metadata={"file_name": "simple.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Simple JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(simple_doc)

        assert len(chunks) >= 1

    def test_chunk_document_large_elements_splitting(self, json_strategy):
        """Test chunking with large elements that need splitting."""
        # Create a document with large elements
        large_object = {f"key_{i}": "x" * 100 for i in range(50)}
        doc = Document(
            content=json.dumps(large_object),
            metadata={"file_name": "large_object.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Large Object JSON",
            content_type="json",
        )

        # Set small chunk size to force splitting
        json_strategy.chunk_size = 500

        chunks = json_strategy.chunk_document(doc)

        assert len(chunks) > 1

    def test_chunk_document_exception_handling(
        self, json_strategy, sample_json_document
    ):
        """Test exception handling during chunking."""
        with patch.object(
            json_strategy, "_parse_json_structure", side_effect=Exception("Test error")
        ):
            chunks = json_strategy.chunk_document(sample_json_document)

            # Should fallback to simple chunking
            assert len(chunks) > 0
            assert chunks[0].metadata.get("chunking_method") == "fallback_text"

    def test_create_optimized_chunk_document_with_nlp(
        self, json_strategy, sample_json_document
    ):
        """Test creating optimized chunk document with NLP processing."""
        with patch.object(
            json_strategy,
            "_process_text",
            return_value={
                "entities": [{"text": "test", "label": "TEST"}],
                "pos_tags": [("test", "NOUN")],
            },
        ):
            chunk_doc = json_strategy._create_optimized_chunk_document(
                original_doc=sample_json_document,
                chunk_content="test content",
                chunk_index=0,
                total_chunks=1,
                skip_nlp=False,
            )

            assert chunk_doc.content == "test content"
            assert chunk_doc.metadata["chunk_index"] == 0
            assert chunk_doc.metadata["total_chunks"] == 1
            assert chunk_doc.metadata["nlp_skipped"] is False
            assert "entities" in chunk_doc.metadata

    def test_create_optimized_chunk_document_skip_nlp(
        self, json_strategy, sample_json_document
    ):
        """Test creating optimized chunk document with NLP skipped."""
        chunk_doc = json_strategy._create_optimized_chunk_document(
            original_doc=sample_json_document,
            chunk_content="test content",
            chunk_index=0,
            total_chunks=1,
            skip_nlp=True,
        )

        assert chunk_doc.content == "test content"
        assert chunk_doc.metadata["nlp_skipped"] is True
        assert chunk_doc.metadata["skip_reason"] == "chunk_too_large"
        assert chunk_doc.metadata["entities"] == []

    def test_create_optimized_chunk_document_nlp_error(
        self, json_strategy, sample_json_document
    ):
        """Test creating optimized chunk document with NLP processing error."""
        with patch.object(
            json_strategy, "_process_text", side_effect=Exception("NLP error")
        ):
            chunk_doc = json_strategy._create_optimized_chunk_document(
                original_doc=sample_json_document,
                chunk_content="test content",
                chunk_index=0,
                total_chunks=1,
                skip_nlp=False,
            )

            assert chunk_doc.metadata["nlp_skipped"] is True
            assert chunk_doc.metadata["skip_reason"] == "nlp_error"

    def test_fallback_chunking(self, json_strategy, sample_json_document):
        """Test fallback text-based chunking."""
        chunks = json_strategy._fallback_chunking(sample_json_document)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata["chunking_method"] == "fallback_text"
            assert chunk.metadata["parent_document_id"] == sample_json_document.id

    def test_fallback_chunking_large_chunks(self, json_strategy):
        """Test fallback chunking with large chunks that skip NLP."""
        large_content = "\n".join([f"line_{i}" for i in range(1000)])
        doc = Document(
            content=large_content,
            metadata={"file_name": "large.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Large JSON",
            content_type="json",
        )

        # Set small chunk size to create large chunks
        json_strategy.chunk_size = 100

        chunks = json_strategy._fallback_chunking(doc)

        assert len(chunks) > 0
        # Check that chunks are created properly
        # NLP skipping depends on chunk content size vs MAX_CHUNK_SIZE_FOR_NLP
        for chunk in chunks:
            assert chunk.metadata["chunking_method"] == "fallback_text"
            assert chunk.metadata["parent_document_id"] == doc.id

    def test_fallback_chunking_object_limit(self, json_strategy):
        """Test fallback chunking respects object processing limit."""
        # Create content that would generate many chunks
        large_content = "\n".join(
            [f"line_{i}" for i in range(MAX_OBJECTS_TO_PROCESS * 2)]
        )
        doc = Document(
            content=large_content,
            metadata={"file_name": "huge.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Huge JSON",
            content_type="json",
        )

        # Set very small chunk size
        json_strategy.chunk_size = 10

        chunks = json_strategy._fallback_chunking(doc)

        # Should be limited to MAX_OBJECTS_TO_PROCESS
        assert len(chunks) <= MAX_OBJECTS_TO_PROCESS

    def test_split_text(self, json_strategy):
        """Test the _split_text method (required by base class)."""
        text = "This is a test text for splitting."

        result = json_strategy._split_text(text)

        # This method just returns the text as-is (not used in JSON strategy)
        assert result == [text]

    def test_invalid_json(self, json_strategy):
        """Test handling of invalid JSON."""
        invalid_json_doc = Document(
            content='{"invalid": json content}',
            metadata={"file_name": "invalid.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Invalid JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(invalid_json_doc)

        # Should fallback to text chunking
        assert len(chunks) > 0
        assert chunks[0].metadata.get("chunking_method") == "fallback_text"

    def test_large_json_fallback(self, json_strategy):
        """Test fallback for very large JSON files."""
        # Create a large JSON content
        large_content = (
            '{"data": [' + ",".join([f'{{"id": {i}}}' for i in range(10000)]) + "]}"
        )

        large_json_doc = Document(
            content=large_content,
            metadata={"file_name": "large.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Large JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(large_json_doc)

        # Should use simple chunking for large files
        assert len(chunks) > 0

    def test_empty_json(self, json_strategy):
        """Test handling of empty JSON."""
        empty_json_doc = Document(
            content="{}",
            metadata={"file_name": "empty.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Empty JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(empty_json_doc)

        assert len(chunks) >= 1
        assert chunks[0].content == "{}"

    def test_array_json(self, json_strategy):
        """Test handling of JSON arrays."""
        array_json_doc = Document(
            content='[{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]',
            metadata={"file_name": "array.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Array JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(array_json_doc)

        assert len(chunks) >= 1
        # Should have array-related metadata (either array or array_item)
        element_types = [chunk.metadata.get("element_type", "") for chunk in chunks]
        assert any(
            "array" in element_type.lower() or "object" in element_type.lower()
            for element_type in element_types
        )


class TestJSONStrategyIntegration:
    """Integration tests for JSON strategy with complex scenarios."""

    def test_deeply_nested_json(self, json_strategy):
        """Test handling of deeply nested JSON structures."""
        nested_data = {"level_0": {}}
        current = nested_data["level_0"]
        for i in range(10):
            current[f"level_{i+1}"] = {}
            current = current[f"level_{i+1}"]
        current["final_value"] = "deep_value"

        doc = Document(
            content=json.dumps(nested_data),
            metadata={"file_name": "nested.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Nested JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(doc)

        assert len(chunks) > 0

    def test_mixed_data_types_json(self, json_strategy):
        """Test handling of JSON with mixed data types."""
        mixed_data = {
            "string": "text_value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null_value": None,
            "array": [1, "two", 3.0, False, None],
            "object": {
                "nested_string": "nested_value",
                "nested_array": [{"deep": "value"}],
            },
        }

        doc = Document(
            content=json.dumps(mixed_data),
            metadata={"file_name": "mixed.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Mixed Types JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(doc)

        assert len(chunks) > 0
        # Check that metadata includes various data types
        all_metadata = [chunk.metadata for chunk in chunks]
        data_types = []
        for metadata in all_metadata:
            if "data_types" in metadata:
                data_types.extend(metadata["data_types"])

        # Should detect multiple data types
        assert len(set(data_types)) > 1

    def test_large_array_chunking(self, json_strategy):
        """Test chunking of large arrays."""
        large_array = [{"id": i, "data": f"item_{i}"} for i in range(200)]

        doc = Document(
            content=json.dumps(large_array),
            metadata={"file_name": "large_array.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Large Array JSON",
            content_type="json",
        )

        chunks = json_strategy.chunk_document(doc)

        assert len(chunks) > 1  # Should split large array

        # Check that array elements are properly chunked
        array_chunks = [
            c for c in chunks if c.metadata.get("element_type") in ["array", "object"]
        ]
        assert len(array_chunks) > 0

    def test_performance_limits_respected(self, json_strategy):
        """Test that performance limits are respected during processing."""
        # Create structure that would exceed various limits
        large_object = {}

        # Add many top-level keys
        for i in range(MAX_OBJECT_KEYS_TO_PROCESS + 50):
            large_object[f"key_{i}"] = {
                "nested": f"value_{i}",
                "array": list(range(10)),
            }

        doc = Document(
            content=json.dumps(large_object),
            metadata={"file_name": "performance_test.json"},
            source="test_source",
            source_type=SourceType.LOCALFILE,
            url="file://test_source",
            title="Performance Test JSON",
            content_type="json",
        )

        # This should complete without timeout or excessive memory usage
        chunks = json_strategy.chunk_document(doc)

        assert len(chunks) > 0
        assert len(chunks) <= MAX_OBJECTS_TO_PROCESS  # Respects global limit
