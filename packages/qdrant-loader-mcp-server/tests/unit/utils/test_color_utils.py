"""Tests for color utility functions."""

import pytest

from qdrant_loader_mcp_server.utils.color_utils import (
    build_color_query,
    build_color_query_generic,
    get_color_name_for_rationale,
    hex_to_color_name,
    is_valid_hex_color,
)


class TestHexToColorName:
    """Test hex to color name conversion."""

    def test_black_hex(self):
        """Test black color conversion."""
        assert hex_to_color_name("#000000") == "black"
        assert hex_to_color_name("#000") == "black"
        assert hex_to_color_name("000000") == "black"

    def test_white_hex(self):
        """Test white color conversion."""
        assert hex_to_color_name("#FFFFFF") == "white"
        assert hex_to_color_name("#FFF") == "white"

    def test_primary_colors(self):
        """Test primary color conversions."""
        assert hex_to_color_name("#FF0000") == "red"
        assert hex_to_color_name("#00FF00") == "green"
        assert hex_to_color_name("#0000FF") == "blue"

    def test_invalid_hex(self):
        """Test invalid hex codes."""
        assert hex_to_color_name("invalid") is None
        assert hex_to_color_name("") is None
        assert hex_to_color_name("#GGGGGG") is None

    def test_case_insensitive(self):
        """Test that hex codes are case insensitive."""
        assert hex_to_color_name("#ff0000") == "red"
        assert hex_to_color_name("#FF0000") == "red"
        assert hex_to_color_name("#Ff0000") == "red"


class TestBuildColorQuery:
    """Test color query building."""

    def test_build_clothing_query(self):
        """Test building clothing query."""
        assert build_color_query("#000000") == "black clothing"
        assert build_color_query("#FF0000") == "red clothing"

    def test_build_custom_item_type(self):
        """Test building query with custom item type."""
        assert build_color_query("#000000", "jacket") == "black jacket"
        assert build_color_query("#FF0000", "shoes") == "red shoes"

    def test_invalid_hex_returns_none(self):
        """Test that invalid hex returns None."""
        assert build_color_query("invalid") is None
        assert build_color_query("") is None


class TestBuildColorQueryGeneric:
    """Test generic color query building."""

    def test_build_generic_query(self):
        """Test building generic query."""
        assert build_color_query_generic("#000000") == "black items"
        assert build_color_query_generic("#FF0000") == "red items"

    def test_invalid_hex_returns_none(self):
        """Test that invalid hex returns None."""
        assert build_color_query_generic("invalid") is None


class TestGetColorNameForRationale:
    """Test color name for rationale generation."""

    def test_valid_color(self):
        """Test valid color returns color name."""
        assert get_color_name_for_rationale("#000000") == "black"
        assert get_color_name_for_rationale("#FF0000") == "red"

    def test_invalid_color_returns_fallback(self):
        """Test invalid color returns 'colorful' fallback."""
        assert get_color_name_for_rationale("invalid") == "colorful"
        assert get_color_name_for_rationale("") == "colorful"


class TestIsValidHexColor:
    """Test hex color validation."""

    def test_valid_hex_codes(self):
        """Test valid hex codes."""
        assert is_valid_hex_color("#000000") is True
        assert is_valid_hex_color("#000") is True
        assert is_valid_hex_color("000000") is True
        assert is_valid_hex_color("#FF0000") is True
        assert is_valid_hex_color("#fff") is True

    def test_invalid_hex_codes(self):
        """Test invalid hex codes."""
        assert is_valid_hex_color("invalid") is False
        assert is_valid_hex_color("#GGGGGG") is False
        assert is_valid_hex_color("") is False
        assert is_valid_hex_color("#12345") is False  # Wrong length
        assert is_valid_hex_color("#1234567") is False  # Too long

    def test_case_insensitive(self):
        """Test that validation is case insensitive."""
        assert is_valid_hex_color("#ff0000") is True
        assert is_valid_hex_color("#FF0000") is True
        assert is_valid_hex_color("#Ff0000") is True
