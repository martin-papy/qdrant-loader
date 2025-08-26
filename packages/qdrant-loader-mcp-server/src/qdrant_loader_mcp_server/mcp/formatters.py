"""
MCP Response Formatters - Re-export Module.

This module provides comprehensive MCP response formatting through a clean,
modular architecture. The original MCPFormatters class and its methods have been
extracted to the 'formatters' sub-package for better maintainability and testability.

Architecture:
- formatters.basic: Basic search result and attachment formatting
- formatters.intelligence: Analysis and intelligence result formatting
- formatters.lightweight: Efficient lightweight result construction
- formatters.structured: Complex structured data formatting
- formatters.utils: Shared utilities and helper functions
"""

# Re-export the main MCPFormatters class for backward compatibility
# Also re-export specialized formatters for direct access
from .formatters import (
    BasicResultFormatters,
    FormatterUtils,
    IntelligenceResultFormatters,
    LightweightResultFormatters,
    MCPFormatters,
    StructuredResultFormatters,
)

__all__ = [
    "MCPFormatters",
    "BasicResultFormatters",
    "IntelligenceResultFormatters",
    "LightweightResultFormatters",
    "StructuredResultFormatters",
    "FormatterUtils",
]
