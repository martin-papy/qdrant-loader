"""Shared metadata analysis helpers for code chunking strategy."""

from .complexity import calculate_complexity_metrics, calculate_maintainability_index
from .dependencies import build_dependency_graph, is_third_party_import
from .documentation import calculate_doc_coverage
from .entities import extract_entities
from .language_specific import (
    detect_python_version_features,
    extract_c_cpp_metadata,
    extract_java_metadata,
    extract_javascript_metadata,
    extract_language_specific_metadata,
    extract_python_metadata,
)
from .maintainability import calculate_maintainability_metrics
from .patterns import identify_code_patterns
from .performance import analyze_performance_patterns
from .security import analyze_security_patterns
from .testing import identify_test_code

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
