from __future__ import annotations


def identify_test_code(content: str) -> dict[str, int | bool | str]:
    indicators = {
        "is_test_file": False,
        "test_framework": "none",
        "test_count": 0,
        "assertion_count": 0,
        "mock_usage": False,
        "fixture_usage": False,
    }

    content_lower = content.lower()
    indicators["is_test_file"] = any(
        keyword in content_lower
        for keyword in ["test_", "test", "spec", "unittest", "pytest"]
    )

    if "pytest" in content_lower or "@pytest" in content:
        indicators["test_framework"] = "pytest"
    elif "unittest" in content_lower:
        indicators["test_framework"] = "unittest"
    elif "jest" in content_lower or "describe(" in content:
        indicators["test_framework"] = "jest"
    elif "mocha" in content_lower:
        indicators["test_framework"] = "mocha"

    indicators["test_count"] = content.count("def test_") + content.count("it(")

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
    indicators["assertion_count"] = sum(content.count(p) for p in assertion_patterns)

    indicators["mock_usage"] = any(
        k in content_lower for k in ["mock", "stub", "spy", "patch"]
    )
    indicators["fixture_usage"] = any(
        k in content_lower for k in ["fixture", "setup", "teardown"]
    )

    return indicators
