from __future__ import annotations


def identify_code_patterns(content: str) -> dict[str, list[str]]:
    patterns = {
        "design_patterns": [],
        "anti_patterns": [],
        "best_practices": [],
        "code_smells": [],
    }

    content_lower = content.lower()

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

    if content.count("if ") > 5:
        patterns["code_smells"].append("too_many_conditionals")
    if len(content.split("\n")) > 100:
        patterns["code_smells"].append("long_method")
    if content.count("def ") > 20 or content.count("function ") > 20:
        patterns["code_smells"].append("large_class")
    if "global " in content:
        patterns["anti_patterns"].append("global_variables")

    if '"""' in content or "'''" in content:
        patterns["best_practices"].append("documentation")
    if "test_" in content or "Test" in content:
        patterns["best_practices"].append("testing")
    if any(keyword in content for keyword in ["typing", "Type", "Optional"]):
        patterns["best_practices"].append("type_hints")

    return patterns
