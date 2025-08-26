from __future__ import annotations


def analyze_security_patterns(content: str) -> dict[str, list[str]]:
    security_indicators = {
        "potential_vulnerabilities": [],
        "security_practices": [],
        "sensitive_data_handling": [],
    }

    content_lower = content.lower()

    if "eval(" in content_lower:
        security_indicators["potential_vulnerabilities"].append("eval_usage")
    if "exec(" in content_lower:
        security_indicators["potential_vulnerabilities"].append("exec_usage")
    if "sql" in content_lower and any(
        k in content_lower for k in ["select", "insert", "update"]
    ):
        security_indicators["potential_vulnerabilities"].append("sql_queries")
    if "password" in content_lower and "plain" in content_lower:
        security_indicators["potential_vulnerabilities"].append("plaintext_password")

    if any(k in content_lower for k in ["hash", "encrypt", "bcrypt", "pbkdf2"]):
        security_indicators["security_practices"].append("password_hashing")
    if any(k in content_lower for k in ["csrf", "xss", "sanitize"]):
        security_indicators["security_practices"].append("web_security")
    if "https" in content_lower:
        security_indicators["security_practices"].append("secure_transport")

    if any(k in content_lower for k in ["api_key", "secret", "token", "credential"]):
        security_indicators["sensitive_data_handling"].append("credentials")
    if any(k in content_lower for k in ["email", "phone", "ssn", "credit_card"]):
        security_indicators["sensitive_data_handling"].append("pii_data")

    return security_indicators
