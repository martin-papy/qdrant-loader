"""Unit tests for Jira extra_fields configuration and extraction."""

import pytest
from pydantic import HttpUrl, ValidationError
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.jira.config import (
    RESERVED_NAMES,
    JiraExtraField,
    JiraFieldType,
    JiraProjectConfig,
)
from qdrant_loader.connectors.jira.mappers import _extract_extra_field_value


# ─── JiraExtraField Validation Tests ───────────────────────────────────────
class TestJiraExtraFieldValidation:
    """Test JiraExtraField model validation."""

    def test_valid_simple_field(self):
        """Simple field type should not require attr_name."""
        field = JiraExtraField(
            param_name="customfield_10000",
            name="my_custom_field",
            field_type="simple",
        )
        assert field.param_name == "customfield_10000"
        assert field.name == "my_custom_field"
        assert field.field_type == "simple"
        assert field.attr_name is None

    def test_valid_array_field(self):
        """Array field type should not require attr_name."""
        field = JiraExtraField(
            param_name="customfield_10001",
            name="my_array_field",
            field_type="array",
        )
        assert field.field_type == JiraFieldType.ARRAY
        assert field.attr_name is None

    def test_valid_object_field_with_attr_name(self):
        """Object field type requires attr_name."""
        field = JiraExtraField(
            param_name="customfield_10002",
            name="my_object_field",
            field_type="object",
            attr_name="name",
        )
        assert field.field_type == JiraFieldType.OBJECT
        assert field.attr_name == "name"

    def test_valid_array_object_field_with_attr_name(self):
        """Array_object field type requires attr_name."""
        field = JiraExtraField(
            param_name="customfield_10003",
            name="my_array_object_field",
            field_type="array_object",
            attr_name="value",
        )
        assert field.field_type == JiraFieldType.ARRAY_OBJECT
        assert field.attr_name == "value"

    def test_object_field_missing_attr_name_raises(self):
        """Object field type without attr_name should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JiraExtraField(
                param_name="customfield_10002",
                name="my_object_field",
                field_type="object",
                # missing attr_name
            )
        assert "attr_name" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()

    def test_array_object_field_missing_attr_name_raises(self):
        """Array_object field type without attr_name should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JiraExtraField(
                param_name="customfield_10003",
                name="my_array_object_field",
                field_type="array_object",
                # missing attr_name
            )
        assert "attr_name" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()

    def test_simple_field_with_attr_name_raises(self):
        """Simple field type with attr_name should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JiraExtraField(
                param_name="customfield_10000",
                name="my_custom_field",
                field_type="simple",
                attr_name="value",  # not allowed for simple
            )
        assert "attr_name" in str(exc_info.value)

    def test_array_field_with_attr_name_raises(self):
        """Array field type with attr_name should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JiraExtraField(
                param_name="customfield_10001",
                name="my_array_field",
                field_type="array",
                attr_name="value",  # not allowed for array
            )
        assert "attr_name" in str(exc_info.value)

    def test_all_reserved_names_rejected(self):
        """Verify all RESERVED_NAMES are properly rejected."""
        for reserved_name in RESERVED_NAMES:
            with pytest.raises(ValidationError, match="reserved"):
                JiraExtraField(
                    param_name=f"cf_{reserved_name}",
                    name=reserved_name,
                    field_type="simple",
                )

    def test_whitespace_normalization_in_param_name(self):
        """Whitespace in param_name should be stripped."""
        field = JiraExtraField(
            param_name="  customfield_10000  ",
            name="my_field",
            field_type="simple",
        )
        assert field.param_name == "customfield_10000"

    def test_whitespace_normalization_in_name(self):
        """Whitespace in name should be stripped."""
        field = JiraExtraField(
            param_name="customfield_10000",
            name="  my_field  ",
            field_type="simple",
        )
        assert field.name == "my_field"

    def test_whitespace_normalization_in_attr_name(self):
        """Whitespace in attr_name should be stripped."""
        field = JiraExtraField(
            param_name="customfield_10000",
            name="my_field",
            field_type="object",
            attr_name="  attr_name  ",
        )
        assert field.attr_name == "attr_name"

    def test_empty_param_name_raises(self):
        """Empty param_name should raise ValueError."""
        with pytest.raises(ValidationError):
            JiraExtraField(
                param_name="",
                name="my_field",
                field_type="simple",
            )

    def test_empty_name_raises(self):
        """Empty name should raise ValueError."""
        with pytest.raises(ValidationError):
            JiraExtraField(
                param_name="customfield_10000",
                name="",
                field_type="simple",
            )


# ─── validate_extra_fields_unique Tests ───────────────────────────────────


class TestValidateExtraFieldsUnique:
    """Test validation of uniqueness in extra_fields list."""

    def test_unique_param_names_and_names_accepted(self):
        """Extra fields with unique param_names and names should be accepted."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
            extra_fields=[
                JiraExtraField(
                    param_name="customfield_10000",
                    name="field_a",
                    field_type="simple",
                ),
                JiraExtraField(
                    param_name="customfield_10001",
                    name="field_b",
                    field_type="array",
                ),
            ],
        )
        assert len(config.extra_fields) == 2

    def test_duplicate_param_name_raises(self):
        """Duplicate param_name values should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JiraProjectConfig(
                base_url=HttpUrl("https://test.atlassian.net"),
                project_key="TEST",
                source="test-jira",
                source_type=SourceType.JIRA,
                token="test-token",
                email="test@example.com",
                extra_fields=[
                    JiraExtraField(
                        param_name="customfield_10000",
                        name="field_a",
                        field_type="simple",
                    ),
                    JiraExtraField(
                        param_name="customfield_10000",  # duplicate!
                        name="field_b",
                        field_type="simple",
                    ),
                ],
            )
        assert "param_name" in str(exc_info.value)
        assert "unique" in str(exc_info.value).lower()

    def test_duplicate_name_raises(self):
        """Duplicate name values should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JiraProjectConfig(
                base_url=HttpUrl("https://test.atlassian.net"),
                project_key="TEST",
                source="test-jira",
                source_type=SourceType.JIRA,
                token="test-token",
                email="test@example.com",
                extra_fields=[
                    JiraExtraField(
                        param_name="customfield_10000",
                        name="my_field",
                        field_type="simple",
                    ),
                    JiraExtraField(
                        param_name="customfield_10001",
                        name="my_field",  # duplicate!
                        field_type="simple",
                    ),
                ],
            )
        assert "name" in str(exc_info.value)
        assert "unique" in str(exc_info.value).lower()

    def test_three_fields_one_duplicate_param_raises(self):
        """Duplicate param_name among multiple fields should raise."""
        with pytest.raises(ValidationError, match="param_name"):
            JiraProjectConfig(
                base_url=HttpUrl("https://test.atlassian.net"),
                project_key="TEST",
                source="test-jira",
                source_type=SourceType.JIRA,
                token="test-token",
                email="test@example.com",
                extra_fields=[
                    JiraExtraField(
                        param_name="customfield_10000",
                        name="field_a",
                        field_type="simple",
                    ),
                    JiraExtraField(
                        param_name="customfield_10001",
                        name="field_b",
                        field_type="simple",
                    ),
                    JiraExtraField(
                        param_name="customfield_10000",  # duplicate of first
                        name="field_c",
                        field_type="simple",
                    ),
                ],
            )

    def test_empty_extra_fields_accepted(self):
        """Empty extra_fields list should be accepted."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
            extra_fields=[],
        )
        assert config.extra_fields == []

    def test_none_extra_fields_accepted(self):
        """None extra_fields should be accepted."""
        config = JiraProjectConfig(
            base_url=HttpUrl("https://test.atlassian.net"),
            project_key="TEST",
            source="test-jira",
            source_type=SourceType.JIRA,
            token="test-token",
            email="test@example.com",
        )
        assert config.extra_fields is None


# ─── _extract_extra_field_value Tests ──────────────────────────────────────


class TestExtractExtraFieldValue:
    """Test the _extract_extra_field_value function."""

    def test_simple_field_with_scalar_value(self):
        """Simple field should return the raw scalar value."""
        fields = {"customfield_10000": "test_value"}
        value = _extract_extra_field_value(
            fields,
            "customfield_10000",
            "simple",
            None,
        )
        assert value == "test_value"

    def test_simple_field_with_number(self):
        """Simple field should preserve numeric values."""
        fields = {"customfield_10000": 42}
        value = _extract_extra_field_value(
            fields,
            "customfield_10000",
            "simple",
            None,
        )
        assert value == 42

    def test_simple_field_with_boolean(self):
        """Simple field should preserve boolean values."""
        fields = {"customfield_10000": True}
        value = _extract_extra_field_value(
            fields,
            "customfield_10000",
            "simple",
            None,
        )
        assert value is True

    def test_simple_field_missing_param_returns_none(self):
        """Simple field with missing param_name should return None."""
        fields = {"other_field": "value"}
        value = _extract_extra_field_value(
            fields,
            "customfield_10000",
            "simple",
            None,
        )
        assert value is None

    def test_simple_field_with_none_value(self):
        """Simple field with None value should return None."""
        fields = {"customfield_10000": None}
        value = _extract_extra_field_value(
            fields,
            "customfield_10000",
            "simple",
            None,
        )
        assert value is None

    def test_array_field_with_list(self):
        """Array field should return the raw list."""
        fields = {"customfield_10001": ["a", "b", "c"]}
        value = _extract_extra_field_value(
            fields,
            "customfield_10001",
            JiraFieldType.ARRAY,
            None,
        )
        assert value == ["a", "b", "c"]

    def test_array_field_with_empty_list(self):
        """Array field with empty list should return empty list."""
        fields = {"customfield_10001": []}
        value = _extract_extra_field_value(
            fields,
            "customfield_10001",
            JiraFieldType.ARRAY,
            None,
        )
        assert value == []

    def test_array_field_missing_param_returns_none(self):
        """Array field with missing param_name should return None."""
        fields = {"other_field": ["value"]}
        value = _extract_extra_field_value(
            fields,
            "customfield_10001",
            JiraFieldType.ARRAY,
            None,
        )
        assert value is None

    def test_object_field_with_dict_extracts_attr(self):
        """Object field should extract the specified attribute from dict."""
        fields = {
            "customfield_10002": {
                "name": "Project Version",
                "id": "12345",
                "released": True,
            }
        }
        value = _extract_extra_field_value(
            fields,
            "customfield_10002",
            JiraFieldType.OBJECT,
            "name",
        )
        assert value == "Project Version"

    def test_object_field_extracts_different_attr(self):
        """Object field should extract the correct attribute when specified."""
        fields = {
            "customfield_10002": {
                "name": "Project Version",
                "id": "12345",
                "released": True,
            }
        }
        value = _extract_extra_field_value(
            fields,
            "customfield_10002",
            JiraFieldType.OBJECT,
            "id",
        )
        assert value == "12345"

    def test_object_field_missing_attr_returns_none(self):
        """Object field with missing attribute returns None."""
        fields = {
            "customfield_10002": {
                "name": "Project Version",
                "released": True,
            }
        }
        value = _extract_extra_field_value(
            fields,
            "customfield_10002",
            JiraFieldType.OBJECT,
            "missing_attr",
        )
        assert value is None

    def test_object_field_not_dict_returns_none(self):
        """Object field with non-dict value should return None."""
        fields = {"customfield_10002": "not a dict"}
        value = _extract_extra_field_value(
            fields,
            "customfield_10002",
            JiraFieldType.OBJECT,
            "name",
        )
        assert value is None

    def test_object_field_missing_param_returns_none(self):
        """Object field with missing param_name should return None."""
        fields = {"other_field": {"name": "value"}}
        value = _extract_extra_field_value(
            fields,
            "customfield_10002",
            JiraFieldType.OBJECT,
            "name",
        )
        assert value is None

    def test_array_object_field_with_list_of_dicts(self):
        """Array_object field should extract attribute from each dict in list."""
        fields = {
            "customfield_10003": [
                {"name": "v1.0", "id": "100"},
                {"name": "v2.0", "id": "200"},
                {"name": "v3.0", "id": "300"},
            ]
        }
        value = _extract_extra_field_value(
            fields,
            "customfield_10003",
            JiraFieldType.ARRAY_OBJECT,
            "name",
        )
        assert value == ["v1.0", "v2.0", "v3.0"]

    def test_array_object_field_extracts_different_attr(self):
        """Array_object field should extract the correct attribute."""
        fields = {
            "customfield_10003": [
                {"name": "v1.0", "id": "100"},
                {"name": "v2.0", "id": "200"},
            ]
        }
        value = _extract_extra_field_value(
            fields,
            "customfield_10003",
            JiraFieldType.ARRAY_OBJECT,
            "id",
        )
        assert value == ["100", "200"]

    def test_array_object_field_with_empty_list(self):
        """Array_object field with empty list should return empty list."""
        fields = {"customfield_10003": []}
        value = _extract_extra_field_value(
            fields,
            "customfield_10003",
            JiraFieldType.ARRAY_OBJECT,
            "name",
        )
        assert value == []

    def test_array_object_field_skips_non_dict_items(self):
        """Array_object field should skip non-dict items in list."""
        fields = {
            "customfield_10003": [
                {"name": "v1.0", "id": "100"},
                "not a dict",
                {"name": "v2.0", "id": "200"},
                None,
                {"name": "v3.0", "id": "300"},
            ]
        }
        value = _extract_extra_field_value(
            fields,
            "customfield_10003",
            JiraFieldType.ARRAY_OBJECT,
            "name",
        )
        assert value == ["v1.0", "v2.0", "v3.0"]

    def test_array_object_field_not_list_returns_empty_list(self):
        """Array_object field with non-list value should return empty list."""
        fields = {"customfield_10003": "not a list"}
        value = _extract_extra_field_value(
            fields,
            "customfield_10003",
            JiraFieldType.ARRAY_OBJECT,
            "name",
        )
        assert value == []

    def test_array_object_field_missing_param_returns_empty_list(self):
        """Array_object field with missing param_name should return empty list."""
        fields = {"other_field": [{"name": "value"}]}
        value = _extract_extra_field_value(
            fields,
            "customfield_10003",
            JiraFieldType.ARRAY_OBJECT,
            "name",
        )
        assert value == []

    def test_array_object_field_with_missing_attrs(self):
        """Array_object field returns None for missing attributes in items."""
        fields = {
            "customfield_10003": [
                {"name": "v1.0", "id": "100"},
                {"id": "200"},  # missing 'name'
                {"name": "v3.0", "id": "300"},
            ]
        }
        value = _extract_extra_field_value(
            fields,
            "customfield_10003",
            JiraFieldType.ARRAY_OBJECT,
            "name",
        )
        assert value == ["v1.0", None, "v3.0"]
