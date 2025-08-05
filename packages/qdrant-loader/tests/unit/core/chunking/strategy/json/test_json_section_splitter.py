"""Comprehensive tests for JSONSectionSplitter to achieve 80%+ coverage."""

import json
from unittest.mock import Mock, patch

import pytest

from qdrant_loader.core.chunking.strategy.json.json_section_splitter import JSONSectionSplitter
from qdrant_loader.core.chunking.strategy.json.json_document_parser import JSONElement, JSONElementType
from qdrant_loader.core.document import Document
from qdrant_loader.config import Settings


class TestJSONSectionSplitter:
    """Comprehensive tests for JSONSectionSplitter class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock settings with proper nested structure
        self.mock_settings = Mock(spec=Settings)
        
        # Create nested mock structure for JSON config
        mock_json_strategy = Mock()
        mock_json_strategy.max_chunk_size_for_nlp = 1000
        mock_json_strategy.enable_schema_inference = True
        mock_json_strategy.max_objects_to_process = 100
        mock_json_strategy.max_object_keys_to_process = 50
        mock_json_strategy.max_array_items_per_chunk = 10
        
        mock_strategies = Mock()
        mock_strategies.json_strategy = mock_json_strategy
        
        mock_chunking = Mock()
        mock_chunking.strategies = mock_strategies
        mock_chunking.chunk_size = 1500
        mock_chunking.chunk_overlap = 100
        mock_chunking.max_chunks_per_document = 50
        
        mock_global_config = Mock()
        mock_global_config.chunking = mock_chunking
        
        self.mock_settings.global_config = mock_global_config
        
        # Create splitter instance
        self.splitter = JSONSectionSplitter(self.mock_settings)
        
        # Create test document
        self.test_doc = Document(
            content='{"test": "content"}',
            source="test_source",
            source_type="json",
            title="Test Document",
            url="https://test.com",
            content_type="application/json",
            metadata={"original": "metadata"}
        )
        self.test_doc.id = "test_doc_id"

    def test_init(self):
        """Test JSONSectionSplitter initialization."""
        assert self.splitter.settings is self.mock_settings
        assert self.splitter.json_config is self.mock_settings.global_config.chunking.strategies.json_strategy
        assert self.splitter.chunk_size == 1500
        assert self.splitter.chunk_overlap == 100
        assert self.splitter.min_chunk_size == 200

    def test_split_sections_basic(self):
        """Test basic split_sections method (compatibility method)."""
        content = '{"key": "value", "number": 42}'
        
        result = self.splitter.split_sections(content)
        
        assert len(result) == 1
        assert result[0]["content"] == content
        assert result[0]["metadata"] == {}

    def test_split_sections_with_document(self):
        """Test split_sections with document parameter."""
        content = '{"key": "value"}'
        
        result = self.splitter.split_sections(content, self.test_doc)
        
        assert len(result) == 1
        assert result[0]["content"] == content

    def test_split_json_elements_empty_list(self):
        """Test split_json_elements with empty input."""
        result = self.splitter.split_json_elements([])
        
        assert result == []

    def test_split_json_elements_single_small_element(self):
        """Test split_json_elements with single small element."""
        element = JSONElement(
            name="test",
            element_type=JSONElementType.VALUE,
            content="small content",
            value="small content",
            path="$.test",
            level=1,
            size=50,
            item_count=1
        )
        
        result = self.splitter.split_json_elements([element])
        
        # Should be grouped since it's small
        assert len(result) == 1
        assert result[0].name == "test"  # Single element remains unchanged

    def test_split_json_elements_large_element_splitting(self):
        """Test split_json_elements with element that needs splitting."""
        large_content = "x" * 2000  # Larger than chunk_size (1500)
        element = JSONElement(
            name="large_element",
            element_type=JSONElementType.OBJECT,
            content=large_content,
            value={"key": "value"},
            path="$.large",
            level=1,
            size=2000,
            item_count=1
        )
        
        with patch.object(self.splitter, '_split_large_element', return_value=[element]) as mock_split:
            result = self.splitter.split_json_elements([element])
            
            mock_split.assert_called_once_with(element)
            assert len(result) == 1

    def test_split_json_elements_with_limits(self):
        """Test split_json_elements respects max_objects_to_process limit."""
        # Create 5 elements but set limit to 3
        self.splitter.json_config.max_objects_to_process = 3
        elements = []
        for i in range(5):
            elements.append(JSONElement(
                name=f"element_{i}",
                element_type=JSONElementType.VALUE,
                content=f"content_{i}",
                value=f"value_{i}",
                path=f"$.element_{i}",
                level=1,
                size=100,
                item_count=1
            ))
        
        result = self.splitter.split_json_elements(elements)
        
        # Should be limited to 3 elements (after grouping)
        assert len(result) <= 3

    def test_group_small_elements_empty_list(self):
        """Test _group_small_elements with empty input."""
        result = self.splitter._group_small_elements([])
        
        assert result == []

    def test_group_small_elements_large_elements_stay_separate(self):
        """Test that large elements stay separate during grouping."""
        large_element = JSONElement(
            name="large",
            element_type=JSONElementType.OBJECT,
            content="x" * 300,  # Larger than min_chunk_size (200)
            value={"large": "object"},
            path="$.large",
            level=1,
            size=300,
            item_count=1
        )
        
        result = self.splitter._group_small_elements([large_element])
        
        assert len(result) == 1
        assert result[0] is large_element

    def test_group_small_elements_significant_structures_stay_separate(self):
        """Test that significant structures (OBJECT/ARRAY) stay separate."""
        obj_element = JSONElement(
            name="obj",
            element_type=JSONElementType.OBJECT,
            content='{"small": "object"}',
            value={"small": "object"},
            path="$.obj",
            level=1,
            size=50,  # Small but should stay separate due to type
            item_count=1
        )
        
        array_element = JSONElement(
            name="arr",
            element_type=JSONElementType.ARRAY,
            content='[1, 2, 3]',
            value=[1, 2, 3],
            path="$.arr",
            level=1,
            size=50,
            item_count=3
        )
        
        result = self.splitter._group_small_elements([obj_element, array_element])
        
        assert len(result) == 2
        assert result[0] is obj_element
        assert result[1] is array_element

    def test_group_small_elements_many_keys_stay_separate(self):
        """Test that elements with many keys stay separate."""
        many_keys_element = JSONElement(
            name="many_keys",
            element_type=JSONElementType.OBJECT,
            content='{"key1": 1}',
            value={"key1": 1},
            path="$.many_keys",
            level=1,
            size=50,
            item_count=100  # More than max_object_keys_to_process (50)
        )
        
        result = self.splitter._group_small_elements([many_keys_element])
        
        assert len(result) == 1
        assert result[0] is many_keys_element

    def test_group_small_elements_accumulate_small_elements(self):
        """Test that small elements get accumulated and grouped."""
        small_elements = []
        for i in range(5):
            small_elements.append(JSONElement(
                name=f"small_{i}",
                element_type=JSONElementType.VALUE,
                content=f"value_{i}",
                value=f"value_{i}",
                path=f"$.small_{i}",
                level=1,
                size=20,
                item_count=1
            ))
        
        with patch.object(self.splitter, '_create_grouped_element') as mock_create:
            mock_grouped = JSONElement(
                name="grouped",
                element_type=JSONElementType.OBJECT,
                content='{"grouped": "content"}',
                value={"grouped": "content"},
                path="$.grouped",
                level=1,
                size=100,
                item_count=5
            )
            mock_create.return_value = mock_grouped
            
            result = self.splitter._group_small_elements(small_elements)
            
            mock_create.assert_called_once()
            assert len(result) == 1
            assert result[0] is mock_grouped

    def test_group_small_elements_size_threshold_triggers_grouping(self):
        """Test grouping triggers when accumulated size reaches threshold."""
        # Create elements that will exceed min_chunk_size when accumulated
        elements = []
        for i in range(3):
            elements.append(JSONElement(
                name=f"elem_{i}",
                element_type=JSONElementType.VALUE,
                content="x" * 80,  # 80 chars each, 240 total > 200 threshold
                value=f"value_{i}",
                path=f"$.elem_{i}",
                level=1,
                size=80,
                item_count=1
            ))
        
        with patch.object(self.splitter, '_create_grouped_element') as mock_create:
            mock_grouped = JSONElement(
                name="grouped",
                element_type=JSONElementType.OBJECT,
                content='{"grouped": "content"}',
                value={"grouped": "content"},
                path="$.grouped",
                level=1,
                size=240,
                item_count=3
            )
            mock_create.return_value = mock_grouped
            
            result = self.splitter._group_small_elements(elements)
            
            mock_create.assert_called_once()
            assert len(result) == 1

    def test_group_small_elements_count_threshold_triggers_grouping(self):
        """Test grouping triggers when element count reaches threshold."""
        # Set low threshold for testing
        self.splitter.json_config.max_array_items_per_chunk = 3
        
        elements = []
        for i in range(5):  # More than threshold
            elements.append(JSONElement(
                name=f"elem_{i}",
                element_type=JSONElementType.VALUE,
                content="small",
                value=f"value_{i}",
                path=f"$.elem_{i}",
                level=1,
                size=10,
                item_count=1
            ))
        
        with patch.object(self.splitter, '_create_grouped_element') as mock_create:
            mock_grouped = JSONElement(
                name="grouped",
                element_type=JSONElementType.OBJECT,
                content='{"grouped": "content"}',
                value={"grouped": "content"},
                path="$.grouped",
                level=1,
                size=50,
                item_count=3
            )
            mock_create.return_value = mock_grouped
            
            result = self.splitter._group_small_elements(elements)
            
            # Should be called at least once when threshold is reached
            assert mock_create.call_count >= 1

    def test_create_grouped_element_empty_list_raises_error(self):
        """Test _create_grouped_element with empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot group empty list of elements"):
            self.splitter._create_grouped_element([])

    def test_create_grouped_element_single_element_returns_unchanged(self):
        """Test _create_grouped_element with single element returns it unchanged."""
        element = JSONElement(
            name="single",
            element_type=JSONElementType.VALUE,
            content="single content",
            value="single value",
            path="$.single",
            level=1,
            size=50,
            item_count=1
        )
        
        result = self.splitter._create_grouped_element([element])
        
        assert result is element

    def test_create_grouped_element_array_items(self):
        """Test _create_grouped_element with array items creates array."""
        array_items = []
        for i in range(3):
            array_items.append(JSONElement(
                name=f"item_{i}",
                element_type=JSONElementType.ARRAY_ITEM,
                content=f'"value_{i}"',
                value=f"value_{i}",
                path=f"$[{i}]",
                level=2,
                size=10,
                item_count=1
            ))
        
        result = self.splitter._create_grouped_element(array_items)
        
        assert result.element_type == JSONElementType.ARRAY
        assert result.name == "grouped_items_3"
        assert result.item_count == 3
        assert result.level == 2  # Min level from inputs
        assert "grouped_items_3" in result.path

    def test_create_grouped_element_mixed_elements(self):
        """Test _create_grouped_element with mixed elements creates object."""
        mixed_elements = [
            JSONElement(
                name="prop1",
                element_type=JSONElementType.PROPERTY,
                content='"value1"',
                value="value1",
                path="$.prop1",
                level=1,
                size=10,
                item_count=1
            ),
            JSONElement(
                name="prop2",
                element_type=JSONElementType.VALUE,
                content='"value2"',
                value="value2",
                path="$.prop2",
                level=2,
                size=10,
                item_count=1
            )
        ]
        
        result = self.splitter._create_grouped_element(mixed_elements)
        
        assert result.element_type == JSONElementType.OBJECT
        assert result.name == "grouped_elements_2"
        assert result.item_count == 2
        assert result.level == 1  # Min level from inputs

    def test_create_grouped_element_with_root_name_handling(self):
        """Test _create_grouped_element handles 'root' names properly."""
        elements_with_root = [
            JSONElement(
                name="root",
                element_type=JSONElementType.VALUE,
                content='"value1"',
                value="value1",
                path="$.root",
                level=1,
                size=10,
                item_count=1
            ),
            JSONElement(
                name="normal",
                element_type=JSONElementType.VALUE,
                content='"value2"',
                value="value2",
                path="$.normal",
                level=1,
                size=10,
                item_count=1
            )
        ]
        
        result = self.splitter._create_grouped_element(elements_with_root)
        
        # Should handle root name by replacing with item_0
        assert isinstance(result.value, dict)
        assert "item_0" in result.value or "root" in result.value
        assert "normal" in result.value

    def test_create_grouped_element_json_serialization_error(self):
        """Test _create_grouped_element handles JSON serialization errors."""
        # Create elements with non-serializable values - need multiple elements to trigger grouping
        problematic_elements = [
            JSONElement(
                name="problem1",
                element_type=JSONElementType.VALUE,
                content="problematic1",
                value=object(),  # Non-serializable
                path="$.problem1",
                level=1,
                size=10,
                item_count=1
            ),
            JSONElement(
                name="problem2",
                element_type=JSONElementType.VALUE,
                content="problematic2",
                value=object(),  # Non-serializable
                path="$.problem2",
                level=1,
                size=10,
                item_count=1
            )
        ]
        
        result = self.splitter._create_grouped_element(problematic_elements)
        
        # Should fall back to string representation
        assert isinstance(result.content, str)
        assert result.element_type == JSONElementType.OBJECT

    def test_split_large_element_small_element_returns_unchanged(self):
        """Test _split_large_element with small element returns it unchanged."""
        small_element = JSONElement(
            name="small",
            element_type=JSONElementType.VALUE,
            content="small content",
            value="small value",
            path="$.small",
            level=1,
            size=100,  # Less than chunk_size (1500)
            item_count=1
        )
        
        result = self.splitter._split_large_element(small_element)
        
        assert len(result) == 1
        assert result[0] is small_element

    def test_split_large_element_large_array(self):
        """Test _split_large_element with large array."""
        large_array = list(range(25))  # 25 items > max_array_items_per_chunk (10)
        element = JSONElement(
            name="large_array",
            element_type=JSONElementType.ARRAY,
            content=json.dumps(large_array),
            value=large_array,
            path="$.large_array",
            level=1,
            size=2000,
            item_count=25
        )
        
        result = self.splitter._split_large_element(element)
        
        # Should be split into chunks of max_array_items_per_chunk (10) each
        # 25 items = 3 chunks (10, 10, 5)
        assert len(result) == 3
        for i, chunk in enumerate(result):
            assert chunk.name == f"large_array_chunk_{i + 1}"
            assert chunk.element_type == JSONElementType.ARRAY
            assert isinstance(chunk.value, list)

    def test_split_large_element_large_object(self):
        """Test _split_large_element with large object."""
        large_object = {f"key_{i}": f"value_{i}" for i in range(20)}
        element = JSONElement(
            name="large_object",
            element_type=JSONElementType.OBJECT,
            content=json.dumps(large_object),
            value=large_object,
            path="$.large_object",
            level=1,
            size=2000,
            item_count=20
        )
        
        result = self.splitter._split_large_element(element)
        
        # Should be split into multiple object chunks
        assert len(result) >= 1
        for chunk in result:
            assert chunk.element_type == JSONElementType.OBJECT
            assert isinstance(chunk.value, dict)
            assert "large_object_chunk_" in chunk.name

    def test_split_large_element_fallback_line_splitting(self):
        """Test _split_large_element fallback to line splitting for other types."""
        large_content = "\n".join([f"Line {i}" for i in range(100)])  # Many lines
        element = JSONElement(
            name="large_text",
            element_type=JSONElementType.VALUE,
            content=large_content,
            value=large_content,
            path="$.large_text",
            level=1,
            size=len(large_content),
            item_count=1
        )
        
        result = self.splitter._split_large_element(element)
        
        # Check if the element was actually large enough to be split
        if element.size > self.splitter.chunk_size:
            # Should be split by lines
            assert len(result) >= 1
            for chunk in result:
                assert "large_text_chunk_" in chunk.name
                assert chunk.element_type == JSONElementType.VALUE
        else:
            # Element wasn't large enough, should return unchanged
            assert len(result) == 1
            assert result[0] is element

    def test_split_large_element_json_serialization_error_in_array(self):
        """Test _split_large_element handles JSON errors in array splitting."""
        # Create array with non-serializable items
        problematic_array = [1, 2, object(), 4, 5]  # object() is not serializable
        element = JSONElement(
            name="problematic_array",
            element_type=JSONElementType.ARRAY,
            content="[problematic content]",
            value=problematic_array,
            path="$.problematic_array",
            level=1,
            size=2000,
            item_count=5
        )
        
        result = self.splitter._split_large_element(element)
        
        # Should handle error gracefully and still create chunks
        assert len(result) >= 1
        for chunk in result:
            assert isinstance(chunk.content, str)

    def test_split_large_element_json_serialization_error_in_object(self):
        """Test _split_large_element handles JSON errors in object splitting."""
        # Create object with non-serializable values
        problematic_object = {"key1": "value1", "key2": object()}
        element = JSONElement(
            name="problematic_object", 
            element_type=JSONElementType.OBJECT,
            content='{"problematic": "content"}',
            value=problematic_object,
            path="$.problematic_object",
            level=1,
            size=2000,
            item_count=2
        )
        
        result = self.splitter._split_large_element(element)
        
        # Should handle error gracefully
        assert len(result) >= 1
        for chunk in result:
            assert isinstance(chunk.content, str)

    def test_split_large_element_empty_chunks_fallback(self):
        """Test _split_large_element handles edge cases gracefully."""
        # Test with empty content but claims to be large
        element = JSONElement(
            name="edge_case",
            element_type=JSONElementType.VALUE,
            content="",  # Empty content
            value="",
            path="$.edge_case",
            level=1,
            size=2000,  # Claims to be large but empty
            item_count=0
        )
        
        result = self.splitter._split_large_element(element)
        
        # Should handle gracefully - either return original or create valid chunk
        assert len(result) >= 1
        if len(result) == 1 and result[0] is element:
            # Original element returned unchanged
            pass
        else:
            # Chunks were created - verify they're valid
            for chunk in result:
                assert isinstance(chunk, JSONElement)
                assert chunk.name.startswith("edge_case")

    def test_merge_small_sections_empty_list(self):
        """Test merge_small_sections with empty input."""
        result = self.splitter.merge_small_sections([])
        
        assert result == []

    def test_merge_small_sections_large_sections_stay_separate(self):
        """Test merge_small_sections keeps large sections separate."""
        large_section = {
            "content": "x" * 300,  # Larger than min_chunk_size (200)
            "metadata": {"type": "large"}
        }
        
        result = self.splitter.merge_small_sections([large_section])
        
        assert len(result) == 1
        assert result[0] == large_section

    def test_merge_small_sections_small_sections_get_merged(self):
        """Test merge_small_sections merges small sections."""
        small_sections = [
            {"content": "Section 1", "metadata": {"index": 1}},
            {"content": "Section 2", "metadata": {"index": 2}},
            {"content": "Section 3", "metadata": {"index": 3}}
        ]
        
        result = self.splitter.merge_small_sections(small_sections)
        
        assert len(result) == 1
        merged = result[0]
        assert "Section 1" in merged["content"]
        assert "Section 2" in merged["content"]
        assert "Section 3" in merged["content"]
        # Should merge metadata
        assert "index" in merged["metadata"]

    def test_merge_small_sections_size_limit_triggers_split(self):
        """Test merge_small_sections creates new section when size limit reached."""
        # Create sections that together exceed chunk_size
        sections = [
            {"content": "x" * 800, "metadata": {"part": 1}},  # Small individually
            {"content": "x" * 800, "metadata": {"part": 2}}   # But large together (1600 > 1500)
        ]
        
        result = self.splitter.merge_small_sections(sections)
        
        # Should create separate sections due to size limit
        assert len(result) == 2

    def test_merge_small_sections_metadata_merging(self):
        """Test merge_small_sections properly merges metadata."""
        sections = [
            {"content": "Part 1", "metadata": {"key1": "value1", "shared": "original"}},
            {"content": "Part 2", "metadata": {"key2": "value2", "shared": "updated"}},
            {"content": "Part 3"}  # No metadata
        ]
        
        result = self.splitter.merge_small_sections(sections)
        
        assert len(result) == 1
        merged = result[0]
        metadata = merged.get("metadata", {})
        assert "key1" in metadata
        assert "key2" in metadata
        assert metadata["shared"] == "updated"  # Later values should override

    def test_merge_small_sections_missing_content_handling(self):
        """Test merge_small_sections handles missing content gracefully."""
        sections = [
            {"content": "Valid content", "metadata": {"valid": True}},
            {"metadata": {"missing_content": True}},  # No content key
            {"content": "", "metadata": {"empty": True}}  # Empty content
        ]
        
        result = self.splitter.merge_small_sections(sections)
        
        # Should handle gracefully without errors
        assert len(result) == 1
        assert "Valid content" in result[0]["content"]