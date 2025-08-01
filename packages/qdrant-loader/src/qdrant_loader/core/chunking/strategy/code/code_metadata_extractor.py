"""Code metadata extractor for enhanced programming language analysis."""

import re
from typing import Any, Dict, List

import structlog

from qdrant_loader.core.chunking.strategy.base.metadata_extractor import BaseMetadataExtractor
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
        self.code_config = getattr(settings.global_config.chunking.strategies, 'code', None)
    
    def extract_hierarchical_metadata(self, content: str, chunk_metadata: Dict[str, Any], 
                                    document: Document) -> Dict[str, Any]:
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
        metadata.update({
            "dependency_graph": self._build_dependency_graph(content),
            "complexity_metrics": self._calculate_complexity_metrics(content),
            "code_patterns": self._identify_code_patterns(content),
            "documentation_coverage": self._calculate_doc_coverage(content),
            "test_indicators": self._identify_test_code(content),
            "security_indicators": self._analyze_security_patterns(content),
            "performance_indicators": self._analyze_performance_patterns(content),
            "maintainability_metrics": self._calculate_maintainability_metrics(content),
            "content_type": "code"
        })
        
        # Language-specific analysis
        language = chunk_metadata.get('language', 'unknown')
        if language != 'unknown':
            metadata.update(self._extract_language_specific_metadata(content, language))
        
        return metadata
    
    def extract_entities(self, text: str) -> List[str]:
        """Extract code entities like class names, function names, variables.
        
        Args:
            text: Code text to analyze
            
        Returns:
            List of identified code entities
        """
        entities = []
        
        # Extract class names
        class_pattern = r'\b(?:class|interface|struct|enum)\s+([A-Z][a-zA-Z0-9_]*)'
        entities.extend(re.findall(class_pattern, text))
        
        # Extract function/method names
        function_patterns = [
            r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # Python
            r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # JavaScript
            r'\b(?:public|private|protected)?\s*(?:static\s+)?[a-zA-Z_][a-zA-Z0-9_<>]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # Java/C#
        ]
        
        for pattern in function_patterns:
            entities.extend(re.findall(pattern, text))
        
        # Extract constant names (usually uppercase)
        constant_pattern = r'\b([A-Z][A-Z0-9_]{2,})\b'
        entities.extend(re.findall(constant_pattern, text))
        
        # Remove duplicates and return
        return list(set(entities))
    
    def _build_dependency_graph(self, content: str) -> Dict[str, List[str]]:
        """Build dependency graph for code.
        
        Args:
            content: Code content
            
        Returns:
            Dictionary mapping modules/classes to their dependencies
        """
        dependencies = {
            "imports": [],
            "internal_references": [],
            "external_libraries": []
        }
        
        # Extract import statements
        import_patterns = [
            r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',  # Python: import module
            r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import',  # Python: from module import
            r'#include\s*[<"]([^>"]+)[>"]',  # C/C++
            r'require\s*\([\'"]([^\'"]+)[\'"]\)',  # Node.js
            r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',  # ES6
        ]
        
        for pattern in import_patterns:
            imports = re.findall(pattern, content)
            dependencies["imports"].extend(imports)
        
        # Identify external vs internal dependencies
        for imp in dependencies["imports"]:
            if any(keyword in imp.lower() for keyword in ['std', 'system', 'lib', 'framework']):
                dependencies["external_libraries"].append(imp)
            else:
                dependencies["internal_references"].append(imp)
        
        return dependencies
    
    def _calculate_complexity_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate code complexity metrics.
        
        Args:
            content: Code content
            
        Returns:
            Dictionary of complexity metrics
        """
        lines = content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Cyclomatic complexity indicators
        complexity_indicators = [
            'if ', 'elif ', 'else:', 'while ', 'for ', 'try:', 'except:', 'case ',
            '&&', '||', '?', 'and ', 'or ', 'switch'
        ]
        
        cyclomatic_complexity = 1  # Base complexity
        for indicator in complexity_indicators:
            cyclomatic_complexity += content.lower().count(indicator.lower())
        
        # Nesting depth
        max_nesting = 0
        current_nesting = 0
        
        for line in lines:
            stripped = line.strip()
            if any(keyword in stripped for keyword in ['if', 'for', 'while', 'try', 'def', 'class']):
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif stripped in ['end', '}'] or (stripped.startswith('except') or stripped.startswith('finally')):
                current_nesting = max(0, current_nesting - 1)
        
        return {
            "cyclomatic_complexity": cyclomatic_complexity,
            "lines_of_code": len(non_empty_lines),
            "total_lines": len(lines),
            "max_nesting_depth": max_nesting,
            "complexity_density": cyclomatic_complexity / max(len(non_empty_lines), 1),
            "maintainability_index": self._calculate_maintainability_index(
                len(non_empty_lines), cyclomatic_complexity, content
            )
        }
    
    def _calculate_maintainability_index(self, loc: int, complexity: int, content: str) -> float:
        """Calculate maintainability index (0-100 scale).
        
        Args:
            loc: Lines of code
            complexity: Cyclomatic complexity
            content: Code content
            
        Returns:
            Maintainability index score
        """
        import math
        
        # Simplified maintainability index calculation
        # Based on Halstead metrics and cyclomatic complexity
        
        # Count operators and operands (simplified)
        operators = len(re.findall(r'[+\-*/=<>!&|%^~]', content))
        operands = len(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content))
        
        # Avoid division by zero
        if operands == 0:
            halstead_volume = 0
        else:
            vocabulary = operators + operands
            length = operators + operands
            halstead_volume = length * math.log2(vocabulary) if vocabulary > 1 else 0
        
        # Maintainability index formula (simplified)
        if loc > 0 and halstead_volume > 0:
            mi = 171 - 5.2 * math.log(halstead_volume) - 0.23 * complexity - 16.2 * math.log(loc)
            return max(0, min(100, mi))
        
        return 50  # Default moderate maintainability
    
    def _identify_code_patterns(self, content: str) -> Dict[str, Any]:
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
            "code_smells": []
        }
        
        content_lower = content.lower()
        
        # Design patterns
        if 'singleton' in content_lower or '__new__' in content:
            patterns["design_patterns"].append("singleton")
        if 'factory' in content_lower and ('create' in content_lower or 'build' in content_lower):
            patterns["design_patterns"].append("factory")
        if 'observer' in content_lower or 'notify' in content_lower:
            patterns["design_patterns"].append("observer")
        if 'strategy' in content_lower and 'algorithm' in content_lower:
            patterns["design_patterns"].append("strategy")
        
        # Anti-patterns and code smells
        if content.count('if ') > 10:
            patterns["code_smells"].append("too_many_conditionals")
        if len(content.split('\n')) > 100:
            patterns["code_smells"].append("long_method")
        if content.count('def ') > 20 or content.count('function ') > 20:
            patterns["code_smells"].append("large_class")
        if 'global ' in content:
            patterns["anti_patterns"].append("global_variables")
        
        # Best practices
        if '"""' in content or "'''" in content:
            patterns["best_practices"].append("documentation")
        if 'test_' in content or 'Test' in content:
            patterns["best_practices"].append("testing")
        if any(keyword in content for keyword in ['typing', 'Type', 'Optional']):
            patterns["best_practices"].append("type_hints")
        
        return patterns
    
    def _calculate_doc_coverage(self, content: str) -> Dict[str, Any]:
        """Calculate documentation coverage metrics.
        
        Args:
            content: Code content
            
        Returns:
            Dictionary of documentation metrics
        """
        # Count functions and classes
        function_count = content.count('def ') + content.count('function ')
        class_count = content.count('class ')
        
        # Count docstrings
        docstring_count = content.count('"""') // 2 + content.count("'''") // 2
        
        # Count comments
        comment_lines = len([line for line in content.split('\n') 
                           if line.strip().startswith(('#', '//', '/*'))])
        
        total_elements = function_count + class_count
        doc_coverage = (docstring_count / total_elements * 100) if total_elements > 0 else 0
        
        return {
            "total_functions": function_count,
            "total_classes": class_count,
            "documented_elements": docstring_count,
            "comment_lines": comment_lines,
            "documentation_coverage_percent": doc_coverage,
            "has_module_docstring": content.strip().startswith('"""') or content.strip().startswith("'''"),
            "avg_comment_density": comment_lines / len(content.split('\n')) if content else 0
        }
    
    def _identify_test_code(self, content: str) -> Dict[str, Any]:
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
            "fixture_usage": False
        }
        
        content_lower = content.lower()
        
        # Check if it's a test file
        test_keywords = ['test_', 'test', 'spec', 'unittest', 'pytest']
        test_indicators["is_test_file"] = any(keyword in content_lower for keyword in test_keywords)
        
        # Identify test framework
        if 'pytest' in content_lower or '@pytest' in content:
            test_indicators["test_framework"] = "pytest"
        elif 'unittest' in content_lower:
            test_indicators["test_framework"] = "unittest"
        elif 'jest' in content_lower or 'describe(' in content:
            test_indicators["test_framework"] = "jest"
        elif 'mocha' in content_lower:
            test_indicators["test_framework"] = "mocha"
        
        # Count tests and assertions
        test_indicators["test_count"] = content.count('def test_') + content.count('it(')
        
        assertion_patterns = ['assert', 'expect(', 'should', 'assertEqual', 'assertTrue']
        test_indicators["assertion_count"] = sum(content.count(pattern) for pattern in assertion_patterns)
        
        # Check for mocking and fixtures
        test_indicators["mock_usage"] = any(keyword in content_lower 
                                          for keyword in ['mock', 'stub', 'spy', 'patch'])
        test_indicators["fixture_usage"] = any(keyword in content_lower 
                                             for keyword in ['fixture', 'setup', 'teardown'])
        
        return test_indicators
    
    def _analyze_security_patterns(self, content: str) -> Dict[str, Any]:
        """Analyze security-related patterns in code.
        
        Args:
            content: Code content
            
        Returns:
            Dictionary of security indicators
        """
        security_indicators = {
            "potential_vulnerabilities": [],
            "security_practices": [],
            "sensitive_data_handling": []
        }
        
        content_lower = content.lower()
        
        # Potential vulnerabilities
        if 'eval(' in content_lower:
            security_indicators["potential_vulnerabilities"].append("eval_usage")
        if 'exec(' in content_lower:
            security_indicators["potential_vulnerabilities"].append("exec_usage")
        if 'sql' in content_lower and any(keyword in content_lower for keyword in ['select', 'insert', 'update']):
            security_indicators["potential_vulnerabilities"].append("sql_queries")
        if 'password' in content_lower and 'plain' in content_lower:
            security_indicators["potential_vulnerabilities"].append("plaintext_password")
        
        # Security practices
        if any(keyword in content_lower for keyword in ['hash', 'encrypt', 'bcrypt', 'pbkdf2']):
            security_indicators["security_practices"].append("password_hashing")
        if any(keyword in content_lower for keyword in ['csrf', 'xss', 'sanitize']):
            security_indicators["security_practices"].append("web_security")
        if 'https' in content_lower:
            security_indicators["security_practices"].append("secure_transport")
        
        # Sensitive data patterns
        if any(keyword in content_lower for keyword in ['api_key', 'secret', 'token', 'credential']):
            security_indicators["sensitive_data_handling"].append("credentials")
        if any(keyword in content_lower for keyword in ['email', 'phone', 'ssn', 'credit_card']):
            security_indicators["sensitive_data_handling"].append("pii_data")
        
        return security_indicators
    
    def _analyze_performance_patterns(self, content: str) -> Dict[str, Any]:
        """Analyze performance-related patterns in code.
        
        Args:
            content: Code content
            
        Returns:
            Dictionary of performance indicators
        """
        performance_indicators = {
            "optimization_patterns": [],
            "potential_bottlenecks": [],
            "resource_usage": []
        }
        
        content_lower = content.lower()
        
        # Optimization patterns
        if any(keyword in content_lower for keyword in ['cache', 'memoize', 'lazy']):
            performance_indicators["optimization_patterns"].append("caching")
        if 'async' in content_lower or 'await' in content_lower:
            performance_indicators["optimization_patterns"].append("asynchronous")
        if any(keyword in content_lower for keyword in ['parallel', 'concurrent', 'threading']):
            performance_indicators["optimization_patterns"].append("concurrency")
        
        # Potential bottlenecks
        nested_loops = content.count('for ') * content.count('while ')
        if nested_loops > 3:
            performance_indicators["potential_bottlenecks"].append("nested_loops")
        if content.count('database') > 5 or content.count('query') > 5:
            performance_indicators["potential_bottlenecks"].append("database_heavy")
        if content.count('file') > 10 or content.count('read') > 10:
            performance_indicators["potential_bottlenecks"].append("io_heavy")
        
        # Resource usage
        if any(keyword in content_lower for keyword in ['memory', 'buffer', 'allocation']):
            performance_indicators["resource_usage"].append("memory_management")
        if any(keyword in content_lower for keyword in ['connection', 'pool', 'socket']):
            performance_indicators["resource_usage"].append("connection_management")
        
        return performance_indicators
    
    def _calculate_maintainability_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate maintainability-related metrics.
        
        Args:
            content: Code content
            
        Returns:
            Dictionary of maintainability metrics
        """
        lines = content.split('\n')
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
            "estimated_read_time_minutes": len(non_empty_lines) / 50  # ~50 lines per minute
        }
    
    def _extract_language_specific_metadata(self, content: str, language: str) -> Dict[str, Any]:
        """Extract language-specific metadata.
        
        Args:
            content: Code content
            language: Programming language
            
        Returns:
            Language-specific metadata
        """
        metadata = {"language_features": []}
        
        if language == "python":
            metadata.update(self._extract_python_metadata(content))
        elif language in ["javascript", "typescript"]:
            metadata.update(self._extract_javascript_metadata(content))
        elif language == "java":
            metadata.update(self._extract_java_metadata(content))
        elif language in ["cpp", "c"]:
            metadata.update(self._extract_c_cpp_metadata(content))
        
        return metadata
    
    def _extract_python_metadata(self, content: str) -> Dict[str, Any]:
        """Extract Python-specific metadata."""
        features = []
        
        if 'async def' in content:
            features.append("async_functions")
        if '@' in content:
            features.append("decorators")
        if 'typing' in content or 'Type' in content:
            features.append("type_hints")
        if 'yield' in content:
            features.append("generators")
        if '__' in content:
            features.append("dunder_methods")
        if 'lambda' in content:
            features.append("lambda_functions")
        
        return {
            "language_features": features,
            "python_version_indicators": self._detect_python_version_features(content)
        }
    
    def _extract_javascript_metadata(self, content: str) -> Dict[str, Any]:
        """Extract JavaScript/TypeScript-specific metadata."""
        features = []
        
        if 'async' in content and 'await' in content:
            features.append("async_await")
        if '=>' in content:
            features.append("arrow_functions")
        if 'const' in content or 'let' in content:
            features.append("es6_variables")
        if 'class' in content:
            features.append("es6_classes")
        if 'import' in content and 'from' in content:
            features.append("es6_modules")
        if '${' in content:
            features.append("template_literals")
        
        return {"language_features": features}
    
    def _extract_java_metadata(self, content: str) -> Dict[str, Any]:
        """Extract Java-specific metadata."""
        features = []
        
        if 'interface' in content:
            features.append("interfaces")
        if 'extends' in content:
            features.append("inheritance")
        if 'implements' in content:
            features.append("interface_implementation")
        if 'synchronized' in content:
            features.append("thread_synchronization")
        if 'generic' in content or '<' in content and '>' in content:
            features.append("generics")
        if '@Override' in content or '@' in content:
            features.append("annotations")
        
        return {"language_features": features}
    
    def _extract_c_cpp_metadata(self, content: str) -> Dict[str, Any]:
        """Extract C/C++-specific metadata."""
        features = []
        
        if '#include' in content:
            features.append("header_includes")
        if 'malloc' in content or 'free' in content:
            features.append("manual_memory_management")
        if 'pointer' in content or '->' in content:
            features.append("pointer_usage")
        if 'template' in content:
            features.append("templates")
        if 'namespace' in content:
            features.append("namespaces")
        if 'inline' in content:
            features.append("inline_functions")
        
        return {"language_features": features}
    
    def _detect_python_version_features(self, content: str) -> List[str]:
        """Detect Python version-specific features."""
        features = []
        
        if ':=' in content:
            features.append("walrus_operator_py38")
        if 'match ' in content and 'case ' in content:
            features.append("pattern_matching_py310")
        if 'f"' in content or "f'" in content:
            features.append("f_strings_py36")
        if 'pathlib' in content:
            features.append("pathlib_py34")
        if 'dataclass' in content:
            features.append("dataclasses_py37")
        
        return features 