"""
Template Operations - Template Loading and Processing.

This module handles template loading, placeholder replacement,
and template-related operations for the website builder.
"""

from pathlib import Path


class TemplateProcessor:
    """Handles template loading and processing operations."""

    def __init__(self, templates_dir: str = "website/templates"):
        """Initialize template processor."""
        self.templates_dir = Path(templates_dir)

    def load_template(self, template_name: str) -> str:
        """Load a template file."""
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, encoding="utf-8") as f:
            return f.read()

    def replace_placeholders(self, content: str, replacements: dict[str, str]) -> str:
        """Replace placeholders in content with actual values."""
        for placeholder, value in replacements.items():
            content = content.replace(f"{{{{ {placeholder} }}}}", str(value))
        return content
