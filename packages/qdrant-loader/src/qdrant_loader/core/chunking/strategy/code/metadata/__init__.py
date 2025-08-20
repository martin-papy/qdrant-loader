"""Shared metadata analysis helpers for code chunking strategy."""

from .dependencies import build_dependency_graph, is_third_party_import
from .complexity import calculate_complexity_metrics, calculate_maintainability_index
from .patterns import identify_code_patterns
from .documentation import calculate_doc_coverage
from .testing import identify_test_code
from .security import analyze_security_patterns
from .performance import analyze_performance_patterns
from .maintainability import calculate_maintainability_metrics
from .language_specific import (
    extract_language_specific_metadata,
    extract_python_metadata,
    extract_javascript_metadata,
    extract_java_metadata,
    extract_c_cpp_metadata,
    detect_python_version_features,
)
from .entities import extract_entities

__all__ = [
    "build_dependency_graph",
    "is_third_party_import",
    "calculate_complexity_metrics",
    "calculate_maintainability_index",
    "identify_code_patterns",
    "calculate_doc_coverage",
    "identify_test_code",
    "analyze_security_patterns",
    "analyze_performance_patterns",
    "calculate_maintainability_metrics",
    "extract_language_specific_metadata",
    "extract_python_metadata",
    "extract_javascript_metadata",
    "extract_java_metadata",
    "extract_c_cpp_metadata",
    "detect_python_version_features",
    "extract_entities",
]


