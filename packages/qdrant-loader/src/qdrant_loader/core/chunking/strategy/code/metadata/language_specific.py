from __future__ import annotations

from typing import Any


def extract_language_specific_metadata(content: str, language: str) -> dict[str, Any]:
    if language == "python":
        return extract_python_metadata(content)
    elif language in ["javascript", "typescript"]:
        return extract_javascript_metadata(content)
    elif language == "java":
        return extract_java_metadata(content)
    elif language in ["cpp", "c"]:
        return extract_c_cpp_metadata(content)
    else:
        return {}


def extract_python_metadata(content: str) -> dict[str, Any]:
    features: list[str] = []
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
        "python_version_indicators": detect_python_version_features(content),
    }


def extract_javascript_metadata(content: str) -> dict[str, Any]:
    features: list[str] = []
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


def extract_java_metadata(content: str) -> dict[str, Any]:
    features: list[str] = []
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


def extract_c_cpp_metadata(content: str) -> dict[str, Any]:
    features: list[str] = []
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


def detect_python_version_features(content: str) -> list[str]:
    features: list[str] = []
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
