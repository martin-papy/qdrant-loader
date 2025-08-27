"""Code metadata extractor for enhanced programming language analysis."""

import re
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

        # Add enhanced code analysis
        metadata.update(
            {
                "dependency_graph": self._build_dependency_graph(content),
                "complexity_metrics": self._calculate_complexity_metrics(content),
                "code_patterns": self._identify_code_patterns(content),
                "documentation_coverage": self._calculate_doc_coverage(content),
                "test_indicators": self._identify_test_code(content),
                "security_indicators": self._analyze_security_patterns(content),
                "performance_indicators": self._analyze_performance_patterns(content),
                "maintainability_metrics": self._calculate_maintainability_metrics(
                    content
                ),
                "content_type": "code",
            }
        )

        # Language-specific analysis
        language = chunk_metadata.get("language", "unknown")
        if language != "unknown":
            metadata.update(self._extract_language_specific_metadata(content, language))

        return metadata

    def extract_entities(self, text: str) -> list[str]:
        """Extract code entities like class names, function names, variables.

        Args:
            text: Code text to analyze

        Returns:
            List of identified code entities
        """
        entities = []

        # Extract class names
        class_pattern = r"\b(?:class|interface|struct|enum)\s+([A-Z][a-zA-Z0-9_]*)"
        entities.extend(re.findall(class_pattern, text))

        # Extract function/method names
        function_patterns = [
            r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # Python
            r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)",  # JavaScript
            r"\b(?:public|private|protected)?\s*(?:static\s+)?[a-zA-Z_][a-zA-Z0-9_<>]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",  # Java/C#
        ]

        for pattern in function_patterns:
            entities.extend(re.findall(pattern, text))

        # Extract constant names (usually uppercase)
        constant_pattern = r"\b([A-Z][A-Z0-9_]{2,})\b"
        entities.extend(re.findall(constant_pattern, text))

        # Remove duplicates and return
        return list(set(entities))

    def _build_dependency_graph(self, content: str) -> dict[str, list[str]]:
        """Build dependency graph for code.

        Args:
            content: Code content

        Returns:
            Dictionary mapping modules/classes to their dependencies
        """
        dependencies = {
            "imports": [],
            "internal_references": [],
            "third_party_imports": [],
            "stdlib_imports": [],
        }

        # Extract import statements
        import_patterns = [
            r"import\s+([a-zA-Z_][a-zA-Z0-9_.]*)",  # Python: import module
            r"from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import",  # Python: from module import
            r'#include\s*[<"]([^>"]+)[>"]',  # C/C++
            r'require\s*\([\'"]([^\'"]+)[\'"]\)',  # Node.js
            r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',  # ES6
        ]

        for pattern in import_patterns:
            imports = re.findall(pattern, content)
            dependencies["imports"].extend(imports)

        # Python standard library modules (common ones)
        python_stdlib = {
            "os",
            "sys",
            "json",
            "math",
            "random",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "operator",
            "re",
            "urllib",
            "http",
            "pathlib",
            "typing",
            "dataclasses",
            "abc",
            "enum",
            "logging",
            "threading",
            "multiprocessing",
            "subprocess",
            "socket",
            "sqlite3",
            "csv",
            "pickle",
            "gzip",
            "zipfile",
            "tarfile",
            "shutil",
            "tempfile",
        }

        # Identify external vs internal vs stdlib dependencies
        for imp in dependencies["imports"]:
            base_module = imp.split(".")[0]
            if base_module in python_stdlib:
                dependencies["stdlib_imports"].append(imp)
            elif self._is_third_party_import(imp):
                dependencies["third_party_imports"].append(imp)
            else:
                dependencies["internal_references"].append(imp)

        return dependencies

    def _is_third_party_import(self, import_name: str) -> bool:
        """Determine if an import is a third-party library.

        Args:
            import_name: The import name to check

        Returns:
            True if it's likely a third-party import
        """
        base_module = import_name.split(".")[0].lower()

        # Known third-party libraries
        known_third_party = {
            "requests",
            "numpy",
            "pandas",
            "flask",
            "django",
            "fastapi",
            "tensorflow",
            "torch",
            "pytorch",
            "sklearn",
            "scipy",
            "matplotlib",
            "seaborn",
            "plotly",
            "streamlit",
            "dash",
            "celery",
            "redis",
            "sqlalchemy",
            "alembic",
            "pydantic",
            "marshmallow",
            "click",
            "typer",
            "pytest",
            "unittest2",
            "mock",
            "httpx",
            "aiohttp",
            "websockets",
            "uvicorn",
            "gunicorn",
            "jinja2",
            "mako",
            "babel",
            "pillow",
            "opencv",
            "cv2",
            "boto3",
            "azure",
            "google",
        }

        if base_module in known_third_party:
            return True

        # Heuristics for third-party libraries:
        # 1. Contains common third-party patterns
        if any(pattern in base_module for pattern in ["lib", "client", "sdk", "api"]):
            return True

        # 2. Looks like a package name (contains underscores but not starting with _)
        if "_" in base_module and not base_module.startswith("_"):
            return True

        # 3. Single lowercase word that's not obviously internal
        if (
            base_module.islower()
            and not base_module.startswith("test")
            and base_module not in ["main", "app", "config", "utils", "helpers"]
        ):
            return True

        return False

    def _calculate_complexity_metrics(self, content: str) -> dict[str, Any]:
        """Calculate code complexity metrics.

        Args:
            content: Code content

        Returns:
            Dictionary of complexity metrics
        """
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # Cyclomatic complexity indicators
        complexity_indicators = [
            "if ",
            "elif ",
            "else:",
            "while ",
            "for ",
            "try:",
            "except:",
            "case ",
            "&&",
            "||",
            "?",
            "and ",
            "or ",
            "switch",
        ]

        cyclomatic_complexity = 1  # Base complexity
        for indicator in complexity_indicators:
            cyclomatic_complexity += content.lower().count(indicator.lower())

        # Nesting depth
        max_nesting = 0
        current_nesting = 0

        for line in lines:
            stripped = line.strip()
            if any(
                keyword in stripped
                for keyword in ["if", "for", "while", "try", "def", "class"]
            ):
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif stripped in ["end", "}"] or (
                stripped.startswith("except") or stripped.startswith("finally")
            ):
                current_nesting = max(0, current_nesting - 1)

        return {
            "cyclomatic_complexity": cyclomatic_complexity,
            "lines_of_code": len(non_empty_lines),
            "total_lines": len(lines),
            "nesting_depth": max_nesting,
            "complexity_density": cyclomatic_complexity / max(len(non_empty_lines), 1),
            "maintainability_index": self._calculate_maintainability_index(content),
        }

    def _calculate_maintainability_index(self, content: str) -> float:
        """Calculate maintainability index (0-100 scale).

        Args:
            content: Code content

        Returns:
            Maintainability index score
        """
        import math

        if not content.strip():
            return 50  # Default for empty content

        # Calculate lines of code and complexity
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]
        loc = len(non_empty_lines)

        # Simple cyclomatic complexity
        complexity_indicators = [
            "if ",
            "elif ",
            "else:",
            "while ",
            "for ",
            "try:",
            "except:",
            "case ",
        ]
        complexity = 1  # Base complexity
        for indicator in complexity_indicators:
            complexity += content.lower().count(indicator.lower())

        # Simplified maintainability index calculation
        # Based on Halstead metrics and cyclomatic complexity

        # Count operators and operands (simplified)
        operators = len(re.findall(r"[+\-*/=<>!&|%^~]", content))
        operands = len(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", content))

        # Avoid division by zero
        if operands == 0:
            halstead_volume = 0
        else:
            vocabulary = operators + operands
            length = operators + operands
            halstead_volume = length * math.log2(vocabulary) if vocabulary > 1 else 0

        # Maintainability index formula (simplified)
        if loc > 0 and halstead_volume > 0:
            mi = (
                171
                - 5.2 * math.log(halstead_volume)
                - 0.23 * complexity
                - 16.2 * math.log(loc)
            )
            return max(0, min(100, mi))

        return 50  # Default moderate maintainability

    def _identify_code_patterns(self, content: str) -> dict[str, Any]:
        """Identify common code patterns and design elements.

        Args:
            content: Code content

        Returns:
            Dictionary of identified patterns
        """
        patterns = {
            "design_patterns": [],
            "anti_patterns": [],
            "best_practices": [],
            "code_smells": [],
        }

        content_lower = content.lower()

        # Design patterns
        if "singleton" in content_lower or "__new__" in content:
            patterns["design_patterns"].append("singleton")
        if "factory" in content_lower and (
            "create" in content_lower or "build" in content_lower
        ):
            patterns["design_patterns"].append("factory")
        if "observer" in content_lower or "notify" in content_lower:
            patterns["design_patterns"].append("observer")
        if "strategy" in content_lower and "algorithm" in content_lower:
            patterns["design_patterns"].append("strategy")

        # Anti-patterns and code smells
        if content.count("if ") > 5:
            patterns["code_smells"].append("too_many_conditionals")
        if len(content.split("\n")) > 100:
            patterns["code_smells"].append("long_method")
        if content.count("def ") > 20 or content.count("function ") > 20:
            patterns["code_smells"].append("large_class")
        if "global " in content:
            patterns["anti_patterns"].append("global_variables")

        # Best practices
        if '"""' in content or "'''" in content:
            patterns["best_practices"].append("documentation")
        if "test_" in content or "Test" in content:
            patterns["best_practices"].append("testing")
        if any(keyword in content for keyword in ["typing", "Type", "Optional"]):
            patterns["best_practices"].append("type_hints")

        return patterns

    def _calculate_doc_coverage(self, content: str) -> dict[str, Any]:
        """Calculate documentation coverage metrics.

        Args:
            content: Code content

        Returns:
            Dictionary of documentation metrics
        """
        # Count functions and classes using more precise regex patterns
        import re

        # Match function definitions (def at start of line with optional whitespace)
        function_count = len(re.findall(r"^\s*def\s+\w+", content, re.MULTILINE))
        function_count += len(re.findall(r"^\s*function\s+\w+", content, re.MULTILINE))

        # Match class definitions (class at start of line with optional whitespace)
        class_count = len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))

        # Count docstrings
        docstring_count = content.count('"""') // 2 + content.count("'''") // 2

        # Count comments
        comment_lines = len(
            [
                line
                for line in content.split("\n")
                if line.strip().startswith(("#", "//", "/*"))
            ]
        )

        total_elements = function_count + class_count
        doc_coverage = (
            (docstring_count / total_elements * 100) if total_elements > 0 else 0
        )

        return {
            "total_functions": function_count,
            "total_classes": class_count,
            "documented_elements": docstring_count,
            "comment_lines": comment_lines,
            "documentation_coverage_percent": doc_coverage,
            "has_module_docstring": content.strip().startswith('"""')
            or content.strip().startswith("'''"),
            "avg_comment_density": (
                comment_lines / len(content.split("\n")) if content else 0
            ),
        }

    def _identify_test_code(self, content: str) -> dict[str, Any]:
        """Identify test-related code indicators.

        Args:
            content: Code content

        Returns:
            Dictionary of test indicators
        """
        test_indicators = {
            "is_test_file": False,
            "test_framework": "none",
            "test_count": 0,
            "assertion_count": 0,
            "mock_usage": False,
            "fixture_usage": False,
        }

        content_lower = content.lower()

        # Check if it's a test file
        test_keywords = ["test_", "test", "spec", "unittest", "pytest"]
        test_indicators["is_test_file"] = any(
            keyword in content_lower for keyword in test_keywords
        )

        # Identify test framework
        if "pytest" in content_lower or "@pytest" in content:
            test_indicators["test_framework"] = "pytest"
        elif "unittest" in content_lower:
            test_indicators["test_framework"] = "unittest"
        elif "jest" in content_lower or "describe(" in content:
            test_indicators["test_framework"] = "jest"
        elif "mocha" in content_lower:
            test_indicators["test_framework"] = "mocha"

        # Count tests and assertions
        test_indicators["test_count"] = content.count("def test_") + content.count(
            "it("
        )

        assertion_patterns = [
            "assert ",
            "assert(",
            "expect(",
            "should",
            "assertEqual",
            "assertTrue",
            "pytest.raises",
            "self.assert",
            "with pytest.raises",
            "raises(",
        ]
        test_indicators["assertion_count"] = sum(
            content.count(pattern) for pattern in assertion_patterns
        )

        # Check for mocking and fixtures
        test_indicators["mock_usage"] = any(
            keyword in content_lower for keyword in ["mock", "stub", "spy", "patch"]
        )
        test_indicators["fixture_usage"] = any(
            keyword in content_lower for keyword in ["fixture", "setup", "teardown"]
        )

        return test_indicators

    def _analyze_security_patterns(self, content: str) -> dict[str, Any]:
        """Analyze security-related patterns in code.

        Args:
            content: Code content

        Returns:
            Dictionary of security indicators
        """
        security_indicators = {
            "potential_vulnerabilities": [],
            "security_practices": [],
            "sensitive_data_handling": [],
        }

        content_lower = content.lower()

        # Potential vulnerabilities
        if "eval(" in content_lower:
            security_indicators["potential_vulnerabilities"].append("eval_usage")
        if "exec(" in content_lower:
            security_indicators["potential_vulnerabilities"].append("exec_usage")
        if "sql" in content_lower and any(
            keyword in content_lower for keyword in ["select", "insert", "update"]
        ):
            security_indicators["potential_vulnerabilities"].append("sql_queries")
        if "password" in content_lower and "plain" in content_lower:
            security_indicators["potential_vulnerabilities"].append(
                "plaintext_password"
            )

        # Security practices
        if any(
            keyword in content_lower
            for keyword in ["hash", "encrypt", "bcrypt", "pbkdf2"]
        ):
            security_indicators["security_practices"].append("password_hashing")
        if any(keyword in content_lower for keyword in ["csrf", "xss", "sanitize"]):
            security_indicators["security_practices"].append("web_security")
        if "https" in content_lower:
            security_indicators["security_practices"].append("secure_transport")

        # Sensitive data patterns
        if any(
            keyword in content_lower
            for keyword in ["api_key", "secret", "token", "credential"]
        ):
            security_indicators["sensitive_data_handling"].append("credentials")
        if any(
            keyword in content_lower
            for keyword in ["email", "phone", "ssn", "credit_card"]
        ):
            security_indicators["sensitive_data_handling"].append("pii_data")

        return security_indicators

    def _analyze_performance_patterns(self, content: str) -> dict[str, Any]:
        """Analyze performance-related patterns in code.

        Args:
            content: Code content

        Returns:
            Dictionary of performance indicators
        """
        performance_indicators = {
            "optimization_patterns": [],
            "potential_bottlenecks": [],
            "resource_usage": [],
        }

        content_lower = content.lower()

        # Optimization patterns
        if any(keyword in content_lower for keyword in ["cache", "memoize", "lazy"]):
            performance_indicators["optimization_patterns"].append("caching")
        if "async" in content_lower or "await" in content_lower:
            performance_indicators["optimization_patterns"].append("async_programming")
        if any(
            keyword in content_lower
            for keyword in ["parallel", "concurrent", "threading"]
        ):
            performance_indicators["optimization_patterns"].append("concurrency")

        # Potential bottlenecks
        # Detect nested loops by looking for multiple for/while statements
        total_loops = content.count("for ") + content.count("while ")
        if total_loops >= 3:  # 3+ loops likely indicates nesting
            performance_indicators["potential_bottlenecks"].append("nested_loops")

        # Detect recursion patterns (exclude the definition line itself)
        lines = content.split("\n")
        def_pattern = re.compile(
            r"^\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
        )
        for idx, line in enumerate(lines):
            match = def_pattern.match(line)
            if not match:
                continue
            func_name = match.group(1)
            # Count calls to the function name on lines other than the definition line
            bare_call_regex = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
            method_call_regex = re.compile(r"\." + re.escape(func_name) + r"\s*\(")
            call_count = 0
            for j, other_line in enumerate(lines):
                if j == idx:
                    continue
                if bare_call_regex.search(other_line) or method_call_regex.search(
                    other_line
                ):
                    call_count += 1
            if call_count > 0:
                performance_indicators["potential_bottlenecks"].append("recursion")
                break

        if content.count("database") > 5 or content.count("query") > 5:
            performance_indicators["potential_bottlenecks"].append("database_heavy")
        if content.count("file") > 10 or content.count("read") > 10:
            performance_indicators["potential_bottlenecks"].append("io_heavy")

        # Resource usage
        if any(
            keyword in content_lower for keyword in ["memory", "buffer", "allocation"]
        ):
            performance_indicators["resource_usage"].append("memory_allocation")
        if any(
            keyword in content_lower for keyword in ["connection", "pool", "socket"]
        ):
            performance_indicators["resource_usage"].append("connection_management")

        return performance_indicators

    def _calculate_maintainability_metrics(self, content: str) -> dict[str, Any]:
        """Calculate maintainability-related metrics.

        Args:
            content: Code content

        Returns:
            Dictionary of maintainability metrics
        """
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # Calculate various metrics
        avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
        max_line_length = max(len(line) for line in lines) if lines else 0

        # Count long lines (> 120 characters)
        long_lines = len([line for line in lines if len(line) > 120])

        # Calculate code density (non-empty lines / total lines)
        code_density = len(non_empty_lines) / len(lines) if lines else 0

        # Estimate readability score based on various factors
        readability_score = 100
        if avg_line_length > 100:
            readability_score -= 20
        if max_line_length > 200:
            readability_score -= 15
        if long_lines > len(lines) * 0.3:
            readability_score -= 25
        if code_density < 0.5:
            readability_score -= 10

        return {
            "avg_line_length": avg_line_length,
            "max_line_length": max_line_length,
            "long_lines_count": long_lines,
            "code_density": code_density,
            "readability_score": max(0, readability_score),
            "estimated_read_time_minutes": len(non_empty_lines)
            / 50,  # ~50 lines per minute
        }

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
        if language == "python":
            return self._extract_python_metadata(content)
        elif language in ["javascript", "typescript"]:
            return self._extract_javascript_metadata(content)
        elif language == "java":
            return self._extract_java_metadata(content)
        elif language in ["cpp", "c"]:
            return self._extract_c_cpp_metadata(content)
        else:
            # Return empty dict for unknown languages
            return {}

    def _extract_python_metadata(self, content: str) -> dict[str, Any]:
        """Extract Python-specific metadata."""
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

        return {
            "python_features": features,
            "python_version_indicators": self._detect_python_version_features(content),
        }

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
        features = []

        if ":=" in content:
            features.append("walrus_operator_py38")
        if "match " in content and "case " in content:
            features.append("pattern_matching_py310")
        if 'f"' in content or "f'" in content:
            features.append("f_strings_py36")
        if "pathlib" in content:
            features.append("pathlib_py34")
        if "dataclass" in content:
            features.append("dataclasses_py37")

        return features
