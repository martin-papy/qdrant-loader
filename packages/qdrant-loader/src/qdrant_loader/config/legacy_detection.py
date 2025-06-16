"""Legacy configuration detection utilities.

This module provides functionality to detect legacy single-file configurations
and guide users to migrate to the new domain-specific format.
"""

from pathlib import Path

import yaml

from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class LegacyConfigDetector:
    """Detects legacy configuration files and provides migration guidance."""

    def __init__(self):
        """Initialize the legacy configuration detector."""
        # Common legacy configuration file names
        self.legacy_config_patterns = [
            "config.yaml",
            "config.yml",
            "configuration.yaml",
            "configuration.yml",
        ]

        # Domain-specific file names that indicate new format
        self.new_format_files = [
            "connectivity.yaml",
            "connectivity.yml",
            "projects.yaml",
            "projects.yml",
            "fine-tuning.yaml",
            "fine-tuning.yml",
        ]

    def detect_legacy_config(
        self, config_path: Path | None = None, search_dir: Path | None = None
    ) -> tuple[bool, Path | None, str]:
        """Detect if a legacy configuration file is being used.

        Args:
            config_path: Specific config file path to check
            search_dir: Directory to search for config files (defaults to current dir)

        Returns:
            Tuple of (is_legacy, config_file_path, reason)
        """
        if search_dir is None:
            search_dir = Path.cwd()

        # Case 1: Specific config file provided
        if config_path is not None:
            if not config_path.exists():
                return False, None, "Config file does not exist"

            is_legacy, reason = self._is_legacy_config_file(config_path)
            return is_legacy, config_path if is_legacy else None, reason

        # Case 2: Search for config files in directory
        return self._search_for_legacy_configs(search_dir)

    def _search_for_legacy_configs(
        self, search_dir: Path
    ) -> tuple[bool, Path | None, str]:
        """Search for legacy configuration files in a directory.

        Args:
            search_dir: Directory to search

        Returns:
            Tuple of (is_legacy, config_file_path, reason)
        """
        # First, check if new format files exist
        new_format_found = []
        for pattern in self.new_format_files:
            config_file = search_dir / pattern
            if config_file.exists():
                new_format_found.append(pattern)

        # If new format files exist, assume new format is being used
        if new_format_found:
            logger.debug(
                "New format configuration files found",
                files=new_format_found,
                directory=str(search_dir),
            )
            return False, None, f"New format files found: {', '.join(new_format_found)}"

        # Look for legacy configuration files
        for pattern in self.legacy_config_patterns:
            config_file = search_dir / pattern
            if config_file.exists():
                is_legacy, reason = self._is_legacy_config_file(config_file)
                if is_legacy:
                    return True, config_file, reason

        return False, None, "No configuration files found"

    def _is_legacy_config_file(self, config_path: Path) -> tuple[bool, str]:
        """Check if a specific configuration file is in legacy format.

        Args:
            config_path: Path to the configuration file

        Returns:
            Tuple of (is_legacy, reason)
        """
        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                return False, "Configuration is not a dictionary"

            # Check for legacy indicators
            legacy_indicators = self._check_legacy_indicators(config_data)

            if legacy_indicators:
                reason = f"Legacy format detected: {', '.join(legacy_indicators)}"
                logger.debug(
                    "Legacy configuration detected",
                    file=str(config_path),
                    indicators=legacy_indicators,
                )
                return True, reason

            return False, "Configuration appears to be in new format"

        except yaml.YAMLError as e:
            return False, f"Invalid YAML: {e}"
        except Exception as e:
            return False, f"Error reading file: {e}"

    def _check_legacy_indicators(self, config_data: dict) -> list[str]:
        """Check for indicators that suggest legacy configuration format.

        Args:
            config_data: Parsed configuration data

        Returns:
            List of legacy indicators found
        """
        indicators = []

        # Check for 'global' section (strong indicator of legacy format)
        if "global" in config_data:
            global_section = config_data["global"]
            if isinstance(global_section, dict):
                # Check for nested domain sections within global
                domain_sections = []
                for key in [
                    "qdrant",
                    "neo4j",
                    "embedding",
                    "chunking",
                    "file_conversion",
                    "state_management",
                ]:
                    if key in global_section:
                        domain_sections.append(key)

                if domain_sections:
                    indicators.append(
                        f"global section with domains: {', '.join(domain_sections)}"
                    )

        # Check for mixed domain content in single file
        domain_sections_found = []

        # Connectivity domain indicators
        connectivity_keys = ["qdrant", "neo4j", "embedding", "state_management"]
        for key in connectivity_keys:
            if key in config_data:
                domain_sections_found.append(f"connectivity:{key}")

        # Fine-tuning domain indicators
        fine_tuning_keys = ["chunking", "file_conversion"]
        for key in fine_tuning_keys:
            if key in config_data:
                domain_sections_found.append(f"fine-tuning:{key}")

        # Projects domain indicators
        if "projects" in config_data:
            domain_sections_found.append("projects")

        # If we have multiple domains in one file, it's likely legacy
        unique_domains = set(section.split(":")[0] for section in domain_sections_found)
        if len(unique_domains) > 1:
            indicators.append(
                f"multiple domains in single file: {', '.join(sorted(unique_domains))}"
            )

        # Check for specific legacy patterns
        if "global" in config_data and "projects" in config_data:
            indicators.append("global + projects sections (classic legacy pattern)")

        return indicators

    def get_migration_guidance(
        self, legacy_config_path: Path, suggested_output_dir: Path | None = None
    ) -> dict[str, str]:
        """Get migration guidance for a detected legacy configuration.

        Args:
            legacy_config_path: Path to the legacy configuration file
            suggested_output_dir: Suggested output directory for migration

        Returns:
            Dictionary with migration guidance
        """
        if suggested_output_dir is None:
            suggested_output_dir = legacy_config_path.parent

        guidance = {
            "legacy_file": str(legacy_config_path),
            "output_dir": str(suggested_output_dir),
            "dry_run_command": f"qdrant-loader migrate-config --legacy-config {legacy_config_path} --output-dir {suggested_output_dir} --dry-run",
            "migration_command": f"qdrant-loader migrate-config --legacy-config {legacy_config_path} --output-dir {suggested_output_dir}",
            "force_migration_command": f"qdrant-loader migrate-config --legacy-config {legacy_config_path} --output-dir {suggested_output_dir} --force",
        }

        return guidance


def detect_legacy_configuration(
    config_path: Path | None = None, search_dir: Path | None = None
) -> tuple[bool, Path | None, str]:
    """Convenience function to detect legacy configuration.

    Args:
        config_path: Specific config file path to check
        search_dir: Directory to search for config files

    Returns:
        Tuple of (is_legacy, config_file_path, reason)
    """
    detector = LegacyConfigDetector()
    return detector.detect_legacy_config(config_path, search_dir)


def get_migration_guidance(
    legacy_config_path: Path, suggested_output_dir: Path | None = None
) -> dict[str, str]:
    """Convenience function to get migration guidance.

    Args:
        legacy_config_path: Path to the legacy configuration file
        suggested_output_dir: Suggested output directory for migration

    Returns:
        Dictionary with migration guidance
    """
    detector = LegacyConfigDetector()
    return detector.get_migration_guidance(legacy_config_path, suggested_output_dir)
