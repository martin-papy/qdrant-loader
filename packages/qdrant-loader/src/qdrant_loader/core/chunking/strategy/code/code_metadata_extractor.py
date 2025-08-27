"""Code metadata extractor for enhanced programming language analysis."""

from typing import Any

import structlog

from qdrant_loader.core.chunking.strategy.base.metadata_extractor import (
    BaseMetadataExtractor,
)
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)


class CodeMetadataExtractor(BaseMetadataExtractor):
    """Enhanced metadata extractor for code documents."""

    def __init__(self, settings):
        """Initialize the code metadata extractor.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.logger = logger

        # Code-specific configuration
        self.code_config = getattr(
            settings.global_config.chunking.strategies, "code", None
        )

    def extract_hierarchical_metadata(
        self, content: str, chunk_metadata: dict[str, Any], document: Document
    ) -> dict[str, Any]:
        """Extract comprehensive code metadata from chunk content.

        Args:
            content: Code chunk content
            chunk_metadata: Existing chunk metadata
            document: Original document

        Returns:
            Enhanced metadata dictionary
        """
        metadata = chunk_metadata.copy()

        from qdrant_loader.core.chunking.strategy.code.metadata import (
            analyze_performance_patterns,
            analyze_security_patterns,
            build_dependency_graph,
            calculate_complexity_metrics,
            calculate_doc_coverage,
            calculate_maintainability_metrics,
            extract_language_specific_metadata,
            identify_code_patterns,
            identify_test_code,
        )

        metadata.update(
            {
                "dependency_graph": build_dependency_graph(content),
                "complexity_metrics": calculate_complexity_metrics(content),
                "code_patterns": identify_code_patterns(content),
                "documentation_coverage": calculate_doc_coverage(content),
                "test_indicators": identify_test_code(content),
                "security_indicators": analyze_security_patterns(content),
                "performance_indicators": analyze_performance_patterns(content),
                "maintainability_metrics": calculate_maintainability_metrics(content),
                "content_type": "code",
            }
        )

        language = chunk_metadata.get("language", "unknown")
        if language != "unknown":
            metadata.update(extract_language_specific_metadata(content, language))

        return metadata

    def extract_entities(self, text: str) -> list[str]:
        """Extract code entities like class names, function names, variables.

        Args:
            text: Code text to analyze

        Returns:
            List of identified code entities
        """
        from qdrant_loader.core.chunking.strategy.code.metadata import extract_entities

        return extract_entities(text)

    def _build_dependency_graph(self, content: str) -> dict[str, list[str]]:
        """Build dependency graph for code.

        Args:
            content: Code content

        Returns:
            Dictionary mapping modules/classes to their dependencies
        """
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            build_dependency_graph as _build,
        )

        return _build(content)

    def _is_third_party_import(self, import_name: str) -> bool:
        """Determine if an import is a third-party library.

        Args:
            import_name: The import name to check

        Returns:
            True if it's likely a third-party import
        """
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            is_third_party_import as _is,
        )

        return _is(import_name)

    def _calculate_complexity_metrics(self, content: str) -> dict[str, Any]:
        """Calculate code complexity metrics.

        Args:
            content: Code content

        Returns:
            Dictionary of complexity metrics
        """
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            calculate_complexity_metrics as _calc,
        )

        return _calc(content)

    def _calculate_maintainability_index(self, content: str) -> float:
        """Calculate maintainability index (0-100 scale)."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            calculate_maintainability_index as _mi,
        )

        return _mi(content)

    def _identify_code_patterns(self, content: str) -> dict[str, Any]:
        """Identify common code patterns and design elements."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            identify_code_patterns as _identify,
        )

        return _identify(content)

    def _calculate_doc_coverage(self, content: str) -> dict[str, Any]:
        """Calculate documentation coverage metrics."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            calculate_doc_coverage as _doc,
        )

        return _doc(content)

    def _identify_test_code(self, content: str) -> dict[str, Any]:
        """Identify test-related code indicators."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            identify_test_code as _tests,
        )

        return _tests(content)

    def _analyze_security_patterns(self, content: str) -> dict[str, Any]:
        """Analyze security-related patterns in code."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            analyze_security_patterns as _sec,
        )

        return _sec(content)

    def _analyze_performance_patterns(self, content: str) -> dict[str, Any]:
        """Analyze performance-related patterns in code."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            analyze_performance_patterns as _perf,
        )

        return _perf(content)

    def _calculate_maintainability_metrics(self, content: str) -> dict[str, Any]:
        """Calculate maintainability-related metrics."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            calculate_maintainability_metrics as _maint,
        )

        return _maint(content)

    def _extract_language_specific_metadata(
        self, content: str, language: str
    ) -> dict[str, Any]:
        """Extract language-specific metadata.

        Args:
            content: Code content
            language: Programming language

        Returns:
            Language-specific metadata
        """
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            extract_language_specific_metadata as _lang,
        )

        return _lang(content, language)

    def _extract_python_metadata(self, content: str) -> dict[str, Any]:
        """Extract Python-specific metadata."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            detect_python_version_features as _ver,
        )

        features = []
        if "async def" in content or ("async" in content and "await" in content):
            features.append("async_await")
        if "@" in content:
            features.append("decorators")
        if "typing" in content or "Type" in content or ":" in content:
            features.append("type_hints")
        if "yield" in content:
            features.append("generators")
        if "__enter__" in content and "__exit__" in content:
            features.append("context_managers")
        if "__" in content:
            features.append("dunder_methods")
        if "lambda" in content:
            features.append("lambda_functions")
        if "dataclass" in content or "@dataclass" in content:
            features.append("dataclasses")

        return {"python_features": features, "python_version_indicators": _ver(content)}

    def _extract_javascript_metadata(self, content: str) -> dict[str, Any]:
        """Extract JavaScript/TypeScript-specific metadata."""
        features = []
        if "async" in content and "await" in content:
            features.append("async_await")
        if "=>" in content:
            features.append("arrow_functions")
        if "const" in content or "let" in content:
            features.append("es6_variables")
        if "class" in content:
            features.append("es6_classes")
        if "import" in content and "from" in content:
            features.append("es6_modules")
        if "${" in content:
            features.append("template_literals")
        if "{" in content and "}" in content and ("=" in content or "const" in content):
            features.append("destructuring")
        if "function*" in content or "yield" in content:
            features.append("generators")
        return {"javascript_features": features}

    def _extract_java_metadata(self, content: str) -> dict[str, Any]:
        """Extract Java-specific metadata."""
        features = []
        if "interface" in content:
            features.append("interfaces")
        if "extends" in content:
            features.append("inheritance")
        if "implements" in content:
            features.append("interface_implementation")
        if "synchronized" in content:
            features.append("thread_synchronization")
        if "generic" in content or "<" in content and ">" in content:
            features.append("generics")
        if "@Override" in content or "@" in content:
            features.append("annotations")
        return {"language_features": features}

    def _extract_c_cpp_metadata(self, content: str) -> dict[str, Any]:
        """Extract C/C++-specific metadata."""
        features = []
        if "#include" in content:
            features.append("header_includes")
        if "malloc" in content or "free" in content:
            features.append("manual_memory_management")
        if "pointer" in content or "->" in content:
            features.append("pointer_usage")
        if "template" in content:
            features.append("templates")
        if "namespace" in content:
            features.append("namespaces")
        if "inline" in content:
            features.append("inline_functions")
        return {"language_features": features}

    def _detect_python_version_features(self, content: str) -> list[str]:
        """Detect Python version-specific features."""
        from qdrant_loader.core.chunking.strategy.code.metadata import (
            detect_python_version_features as _detect,
        )

        return _detect(content)
