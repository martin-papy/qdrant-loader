"""Enhanced validation error handling for domain-specific configuration validation.

This module provides comprehensive error handling infrastructure for configuration
validation with domain context, severity levels, and user-friendly error messages.
"""

import traceback
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import ValidationError


class ValidationSeverity(Enum):
    """Severity levels for validation errors."""

    CRITICAL = "critical"  # Prevents application from starting
    WARNING = "warning"  # May cause issues but application can continue
    INFO = "info"  # Informational messages for optimization


class ConfigValidationError(Exception):
    """Enhanced validation error with domain context and remediation guidance."""

    def __init__(
        self,
        message: str,
        domain: str,
        file_path: Optional[Path] = None,
        field_path: Optional[str] = None,
        severity: ValidationSeverity = ValidationSeverity.CRITICAL,
        remediation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize configuration validation error.

        Args:
            message: Human-readable error message
            domain: Configuration domain (connectivity, projects, fine-tuning)
            file_path: Path to the configuration file with the error
            field_path: Dot-notation path to the specific field with error
            severity: Severity level of the validation error
            remediation: Suggested remediation steps
            original_error: Original exception that caused this error
        """
        self.message = message
        self.domain = domain
        self.file_path = file_path
        self.field_path = field_path
        self.severity = severity
        self.remediation = remediation
        self.original_error = original_error

        # Create comprehensive error message
        super().__init__(self._format_error_message())

    def _format_error_message(self) -> str:
        """Format a comprehensive error message with context."""
        parts = [
            f"[{self.severity.value.upper()}] {self.domain.title()} Configuration Error"
        ]

        if self.file_path:
            parts.append(f"File: {self.file_path}")

        if self.field_path:
            parts.append(f"Field: {self.field_path}")

        parts.append(f"Error: {self.message}")

        if self.remediation:
            parts.append(f"Solution: {self.remediation}")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for structured reporting."""
        return {
            "message": self.message,
            "domain": self.domain,
            "file_path": str(self.file_path) if self.file_path else None,
            "field_path": self.field_path,
            "severity": self.severity.value,
            "remediation": self.remediation,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class ValidationErrorCollector:
    """Collects and manages validation errors across multiple domains."""

    def __init__(self, fail_fast: bool = False):
        """Initialize error collector.

        Args:
            fail_fast: If True, raise immediately on critical errors
        """
        self.fail_fast = fail_fast
        self.errors: List[ConfigValidationError] = []
        self.warnings: List[ConfigValidationError] = []
        self.info: List[ConfigValidationError] = []

    def add_error(self, error: ConfigValidationError) -> None:
        """Add a validation error to the collector.

        Args:
            error: Validation error to add

        Raises:
            ConfigValidationError: If fail_fast is True and error is critical
        """
        if error.severity == ValidationSeverity.CRITICAL:
            self.errors.append(error)
            if self.fail_fast:
                raise error
        elif error.severity == ValidationSeverity.WARNING:
            self.warnings.append(error)
        else:
            self.info.append(error)

    def add_pydantic_error(
        self,
        pydantic_error: ValidationError,
        domain: str,
        file_path: Optional[Path] = None,
        severity: ValidationSeverity = ValidationSeverity.CRITICAL,
    ) -> None:
        """Convert and add Pydantic validation errors.

        Args:
            pydantic_error: Pydantic ValidationError to convert
            domain: Configuration domain
            file_path: Path to configuration file
            severity: Severity level for the errors
        """
        for error in pydantic_error.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_type = error["type"]

            # Create user-friendly message based on error type
            user_message = self._format_pydantic_error(error_type, message, field_path)
            remediation = self._get_remediation_for_error(
                error_type, field_path, domain
            )

            config_error = ConfigValidationError(
                message=user_message,
                domain=domain,
                file_path=file_path,
                field_path=field_path,
                severity=severity,
                remediation=remediation,
                original_error=pydantic_error,
            )

            self.add_error(config_error)

    def _format_pydantic_error(
        self, error_type: str, message: str, field_path: str
    ) -> str:
        """Format Pydantic error into user-friendly message."""
        if error_type == "missing":
            return f"Required field '{field_path}' is missing"
        elif error_type == "type_error":
            return f"Field '{field_path}' has incorrect type: {message}"
        elif error_type == "value_error":
            return f"Field '{field_path}' has invalid value: {message}"
        elif error_type == "url_parsing":
            return f"Field '{field_path}' contains invalid URL format"
        elif error_type == "string_too_short":
            return f"Field '{field_path}' is too short: {message}"
        elif error_type == "string_too_long":
            return f"Field '{field_path}' is too long: {message}"
        elif error_type == "greater_than":
            return f"Field '{field_path}' must be greater than specified minimum: {message}"
        elif error_type == "less_than":
            return (
                f"Field '{field_path}' must be less than specified maximum: {message}"
            )
        else:
            return f"Field '{field_path}': {message}"

    def _get_remediation_for_error(
        self, error_type: str, field_path: str, domain: str
    ) -> str:
        """Get remediation suggestions based on error type and context."""
        if error_type == "missing":
            if domain == "connectivity":
                if "qdrant" in field_path:
                    return (
                        "Add QDrant configuration with url and collection_name fields"
                    )
                elif "embedding" in field_path:
                    return (
                        "Add embedding service configuration with provider and api_key"
                    )
            elif domain == "projects":
                if "projects" in field_path:
                    return (
                        "Add at least one project definition with sources configuration"
                    )
            elif domain == "fine-tuning":
                return f"Add {field_path} configuration with appropriate default values"

        elif error_type == "type_error":
            return f"Check the data type for {field_path} - ensure it matches the expected format"

        elif error_type == "url_parsing":
            return "Ensure URL includes protocol (http:// or https://) and is properly formatted"

        elif error_type in ["greater_than", "less_than"]:
            return f"Adjust {field_path} value to be within the valid range"

        return (
            f"Review the {domain}.yaml file and correct the {field_path} configuration"
        )

    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return len(self.errors) > 0

    def has_any_issues(self) -> bool:
        """Check if there are any issues (errors, warnings, or info)."""
        return len(self.errors) > 0 or len(self.warnings) > 0 or len(self.info) > 0

    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all validation issues."""
        return {
            "critical_errors": len(self.errors),
            "warnings": len(self.warnings),
            "info_messages": len(self.info),
            "total_issues": len(self.errors) + len(self.warnings) + len(self.info),
            "domains_with_errors": list(set(error.domain for error in self.errors)),
            "can_continue": len(self.errors) == 0,
        }

    def format_errors_for_display(
        self, include_warnings: bool = True, include_info: bool = False
    ) -> str:
        """Format all errors for user-friendly display.

        Args:
            include_warnings: Whether to include warning-level issues
            include_info: Whether to include info-level messages

        Returns:
            Formatted error report
        """
        lines = []

        if self.errors:
            lines.append("🚨 CRITICAL ERRORS (must be fixed):")
            lines.append("=" * 50)
            for error in self.errors:
                lines.append(str(error))
                lines.append("")

        if include_warnings and self.warnings:
            lines.append("⚠️  WARNINGS (recommended to fix):")
            lines.append("=" * 50)
            for warning in self.warnings:
                lines.append(str(warning))
                lines.append("")

        if include_info and self.info:
            lines.append("💡 INFORMATION (optimization suggestions):")
            lines.append("=" * 50)
            for info in self.info:
                lines.append(str(info))
                lines.append("")

        # Add summary
        summary = self.get_error_summary()
        lines.append("📊 VALIDATION SUMMARY:")
        lines.append("=" * 50)
        lines.append(f"Critical Errors: {summary['critical_errors']}")
        lines.append(f"Warnings: {summary['warnings']}")
        lines.append(f"Info Messages: {summary['info_messages']}")
        lines.append(f"Can Continue: {'Yes' if summary['can_continue'] else 'No'}")

        if summary["domains_with_errors"]:
            lines.append(
                f"Domains with Issues: {', '.join(summary['domains_with_errors'])}"
            )

        return "\n".join(lines)

    def raise_if_critical(self) -> None:
        """Raise exception if there are critical errors."""
        if self.has_critical_errors():
            error_messages = [str(error) for error in self.errors]
            raise ConfigValidationError(
                message=f"Configuration validation failed with {len(self.errors)} critical error(s)",
                domain="multiple",
                severity=ValidationSeverity.CRITICAL,
                remediation="Fix all critical errors listed above before proceeding",
            )


class DomainValidationContext:
    """Context manager for domain-specific validation with error collection."""

    def __init__(
        self,
        domain: str,
        file_path: Optional[Path] = None,
        error_collector: Optional[ValidationErrorCollector] = None,
    ):
        """Initialize validation context.

        Args:
            domain: Configuration domain being validated
            file_path: Path to configuration file
            error_collector: Error collector to use (creates new one if None)
        """
        self.domain = domain
        self.file_path = file_path
        self.error_collector = error_collector or ValidationErrorCollector()

    def add_error(
        self,
        message: str,
        field_path: Optional[str] = None,
        severity: ValidationSeverity = ValidationSeverity.CRITICAL,
        remediation: Optional[str] = None,
    ) -> None:
        """Add a validation error within this context."""
        error = ConfigValidationError(
            message=message,
            domain=self.domain,
            file_path=self.file_path,
            field_path=field_path,
            severity=severity,
            remediation=remediation,
        )
        self.error_collector.add_error(error)

    def validate_required_field(
        self,
        config: Dict[str, Any],
        field_path: str,
        field_description: str = "",
    ) -> bool:
        """Validate that a required field is present and not empty.

        Args:
            config: Configuration dictionary
            field_path: Dot-notation path to field
            field_description: Human-readable description of field

        Returns:
            True if field is valid, False otherwise
        """
        keys = field_path.split(".")
        current = config

        try:
            for key in keys:
                if not isinstance(current, dict) or key not in current:
                    self.add_error(
                        message=f"Required field '{field_path}' is missing",
                        field_path=field_path,
                        remediation=f"Add {field_description or field_path} to your {self.domain}.yaml file",
                    )
                    return False
                current = current[key]

            if current is None or (isinstance(current, str) and not current.strip()):
                self.add_error(
                    message=f"Required field '{field_path}' is empty",
                    field_path=field_path,
                    remediation=f"Provide a valid value for {field_description or field_path}",
                )
                return False

            return True

        except Exception as e:
            self.add_error(
                message=f"Error accessing field '{field_path}': {str(e)}",
                field_path=field_path,
                remediation=f"Check the structure of {field_path} in your {self.domain}.yaml file",
            )
            return False

    def validate_url_format(self, url: str, field_path: str) -> bool:
        """Validate URL format.

        Args:
            url: URL to validate
            field_path: Field path for error reporting

        Returns:
            True if URL is valid, False otherwise
        """
        import re

        if not url or not isinstance(url, str):
            self.add_error(
                message=f"URL field '{field_path}' is empty or invalid type",
                field_path=field_path,
                remediation="Provide a valid URL with protocol (http:// or https://)",
            )
            return False

        # Check if URL contains environment variable syntax
        env_var_pattern = r"\$\{[^}]+\}"
        if re.search(env_var_pattern, url):
            # For environment variables, we can't validate the actual URL format
            # but we can check if the default value (after :-) looks valid
            default_match = re.search(r"\$\{[^:}]+:-([^}]+)\}", url)
            if default_match:
                default_url = default_match.group(1)
                # Validate the default URL format
                if not default_url.startswith(
                    ("http://", "https://", "bolt://", "neo4j://", "file://")
                ):
                    self.add_error(
                        message=f"Default URL '{default_url}' in environment variable must include protocol",
                        field_path=field_path,
                        severity=ValidationSeverity.WARNING,
                        remediation="Ensure default URL includes protocol (http://, https://, bolt://, neo4j://, or file://)",
                    )
                    return False
            # Environment variable syntax is valid for configuration templates
            return True

        # Standard URL validation for non-environment variables
        if not url.startswith(
            ("http://", "https://", "bolt://", "neo4j://", "file://")
        ):
            self.add_error(
                message=f"URL '{url}' must include protocol (http://, https://, bolt://, neo4j://, or file://)",
                field_path=field_path,
                remediation="Add appropriate protocol prefix to the URL",
            )
            return False

        return True

    def validate_numeric_range(
        self,
        value: Union[int, float],
        field_path: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
    ) -> bool:
        """Validate numeric value is within specified range.

        Args:
            value: Numeric value to validate
            field_path: Field path for error reporting
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            True if value is valid, False otherwise
        """
        if min_value is not None and value < min_value:
            self.add_error(
                message=f"Value {value} for '{field_path}' is below minimum {min_value}",
                field_path=field_path,
                remediation=f"Set {field_path} to a value >= {min_value}",
            )
            return False

        if max_value is not None and value > max_value:
            self.add_error(
                message=f"Value {value} for '{field_path}' exceeds maximum {max_value}",
                field_path=field_path,
                remediation=f"Set {field_path} to a value <= {max_value}",
            )
            return False

        return True
