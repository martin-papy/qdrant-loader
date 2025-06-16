"""Enhanced domain-specific configuration validator with comprehensive validation rules.

This module provides advanced validation for each configuration domain with
detailed error reporting, edge case handling, and cross-domain validation.
"""

import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from ..utils.logging import LoggingConfig
from .domain_models import (
    ConnectivityConfig,
    DomainConfigValidator,
)
from .validation_errors import (
    DomainValidationContext,
    ValidationErrorCollector,
    ValidationSeverity,
)

logger = LoggingConfig.get_logger(__name__)


class EnhancedDomainValidator:
    """Enhanced validator with comprehensive validation rules and error handling."""

    def __init__(self, fail_fast: bool = False, validate_connectivity: bool = False):
        """Initialize enhanced validator.

        Args:
            fail_fast: If True, stop validation on first critical error
            validate_connectivity: If True, perform actual connectivity tests
        """
        self.fail_fast = fail_fast
        self.validate_connectivity = validate_connectivity
        self.base_validator = DomainConfigValidator()

    def validate_all_domains(
        self,
        domain_configs: dict[str, dict[str, Any]],
        domain_files: dict[str, Path],
    ) -> ValidationErrorCollector:
        """Validate all configuration domains with comprehensive error collection.

        Args:
            domain_configs: Raw configuration data for each domain
            domain_files: File paths for each domain

        Returns:
            ValidationErrorCollector with all validation results
        """
        error_collector = ValidationErrorCollector(fail_fast=self.fail_fast)

        # Validate each domain individually
        for domain, config_data in domain_configs.items():
            file_path = domain_files.get(domain)

            if domain == "connectivity":
                self._validate_connectivity_domain(
                    config_data, file_path, error_collector
                )
            elif domain == "projects":
                self._validate_projects_domain(config_data, file_path, error_collector)
            elif domain == "fine-tuning":
                self._validate_fine_tuning_domain(
                    config_data, file_path, error_collector
                )
            else:
                logger.warning(f"Unknown domain: {domain}")

        # Perform cross-domain validation
        self._validate_cross_domain_dependencies(domain_configs, error_collector)

        return error_collector

    def _validate_connectivity_domain(
        self,
        config_data: dict[str, Any],
        file_path: Path | None,
        error_collector: ValidationErrorCollector,
    ) -> None:
        """Validate connectivity domain configuration."""
        context = DomainValidationContext("connectivity", file_path, error_collector)

        try:
            # First, validate with Pydantic model
            try:
                validated_config = self.base_validator.validate_connectivity(
                    config_data
                )
            except ValidationError as e:
                error_collector.add_pydantic_error(e, "connectivity", file_path)
                return  # Can't continue without valid Pydantic model

            # Enhanced connectivity-specific validation
            self._validate_qdrant_config(config_data.get("qdrant", {}), context)
            self._validate_embedding_config(config_data.get("embedding", {}), context)
            self._validate_neo4j_config(config_data.get("neo4j", {}), context)

            # Perform connectivity tests if enabled
            if self.validate_connectivity:
                self._test_actual_connectivity(validated_config, context)

        except Exception as e:
            context.add_error(
                message=f"Unexpected error during connectivity validation: {str(e)}",
                severity=ValidationSeverity.CRITICAL,
                remediation="Check connectivity.yaml file format and structure",
            )

    def _validate_projects_domain(
        self,
        config_data: dict[str, Any],
        file_path: Path | None,
        error_collector: ValidationErrorCollector,
    ) -> None:
        """Validate projects domain configuration."""
        context = DomainValidationContext("projects", file_path, error_collector)

        try:
            # First, validate with Pydantic model
            try:
                validated_config = self.base_validator.validate_projects(config_data)
            except ValidationError as e:
                error_collector.add_pydantic_error(e, "projects", file_path)
                return

            # Enhanced projects-specific validation
            self._validate_project_definitions(config_data.get("projects", {}), context)

        except Exception as e:
            context.add_error(
                message=f"Unexpected error during projects validation: {str(e)}",
                severity=ValidationSeverity.CRITICAL,
                remediation="Check projects.yaml file format and structure",
            )

    def _validate_fine_tuning_domain(
        self,
        config_data: dict[str, Any],
        file_path: Path | None,
        error_collector: ValidationErrorCollector,
    ) -> None:
        """Validate fine-tuning domain configuration."""
        context = DomainValidationContext("fine-tuning", file_path, error_collector)

        try:
            # First, validate with Pydantic model
            try:
                validated_config = self.base_validator.validate_fine_tuning(config_data)
            except ValidationError as e:
                error_collector.add_pydantic_error(e, "fine-tuning", file_path)
                return

            # Enhanced fine-tuning-specific validation
            self._validate_chunking_config(config_data.get("chunking", {}), context)

        except Exception as e:
            context.add_error(
                message=f"Unexpected error during fine-tuning validation: {str(e)}",
                severity=ValidationSeverity.CRITICAL,
                remediation="Check fine-tuning.yaml file format and structure",
            )

    def _validate_qdrant_config(
        self, qdrant_config: dict[str, Any], context: DomainValidationContext
    ) -> None:
        """Validate QDrant configuration with enhanced checks."""
        if not qdrant_config:
            context.add_error(
                message="QDrant configuration is missing",
                field_path="qdrant",
                remediation="Add qdrant section with url and collection_name",
            )
            return

        # Validate required fields
        if not context.validate_required_field(
            qdrant_config, "url", "QDrant database URL"
        ):
            return

        if not context.validate_required_field(
            qdrant_config, "collection_name", "QDrant collection name"
        ):
            return

        # Validate URL format
        url = qdrant_config.get("url", "")
        if url and not context.validate_url_format(url, "qdrant.url"):
            return

    def _validate_embedding_config(
        self, embedding_config: dict[str, Any], context: DomainValidationContext
    ) -> None:
        """Validate embedding service configuration."""
        if not embedding_config:
            context.add_error(
                message="Embedding configuration is missing",
                field_path="embedding",
                remediation="Add embedding section with provider and api_key",
            )
            return

        # Validate required fields
        context.validate_required_field(
            embedding_config, "provider", "embedding service provider"
        )
        context.validate_required_field(
            embedding_config, "api_key", "embedding service API key"
        )

    def _validate_neo4j_config(
        self, neo4j_config: dict[str, Any], context: DomainValidationContext
    ) -> None:
        """Validate Neo4j configuration (optional)."""
        if not neo4j_config:
            return  # Neo4j is optional

        # If Neo4j config is present, validate required fields
        required_fields = ["uri", "user", "password", "database"]
        for field in required_fields:
            context.validate_required_field(neo4j_config, field, f"Neo4j {field}")

    def _validate_project_definitions(
        self, projects_config: dict[str, Any], context: DomainValidationContext
    ) -> None:
        """Validate project definitions structure."""
        if not projects_config:
            context.add_error(
                message="No projects defined",
                field_path="projects",
                remediation="Add at least one project definition",
            )
            return

        # Check if projects is a dict or has projects field
        projects_data = projects_config.get("projects", projects_config)
        if not isinstance(projects_data, dict):
            context.add_error(
                message="Projects must be defined as a dictionary",
                field_path="projects",
                remediation="Define projects as key-value pairs",
            )
            return

        if not projects_data:
            context.add_error(
                message="No projects defined in projects section",
                field_path="projects",
                remediation="Add at least one project with sources configuration",
            )

    def _validate_chunking_config(
        self, chunking_config: dict[str, Any], context: DomainValidationContext
    ) -> None:
        """Validate text chunking configuration."""
        if not chunking_config:
            return

        # Validate chunk size
        chunk_size = chunking_config.get("chunk_size")
        if chunk_size is not None:
            context.validate_numeric_range(
                chunk_size, "chunking.chunk_size", min_value=100, max_value=100000
            )

        # Validate chunk overlap
        chunk_overlap = chunking_config.get("chunk_overlap")
        if chunk_overlap is not None:
            context.validate_numeric_range(
                chunk_overlap, "chunking.chunk_overlap", min_value=0, max_value=1000
            )

    def _validate_cross_domain_dependencies(
        self,
        domain_configs: dict[str, dict[str, Any]],
        error_collector: ValidationErrorCollector,
    ) -> None:
        """Validate dependencies between configuration domains."""
        # Check if projects domain references valid connectivity settings
        if "projects" in domain_configs and "connectivity" in domain_configs:
            self._validate_projects_connectivity_dependency(
                domain_configs["projects"],
                domain_configs["connectivity"],
                error_collector,
            )

    def _validate_projects_connectivity_dependency(
        self,
        projects_config: dict[str, Any],
        connectivity_config: dict[str, Any],
        error_collector: ValidationErrorCollector,
    ) -> None:
        """Validate that projects configuration is compatible with connectivity."""
        context = DomainValidationContext("cross-domain", None, error_collector)

        # Check if QDrant is configured when projects are defined
        if projects_config.get("projects") and not connectivity_config.get("qdrant"):
            context.add_error(
                message="Projects are defined but QDrant connectivity is not configured",
                field_path="connectivity.qdrant",
                remediation="Configure QDrant connection in connectivity.yaml to support project data storage",
            )

    def _test_actual_connectivity(
        self, config: ConnectivityConfig, context: DomainValidationContext
    ) -> None:
        """Test actual connectivity to configured services."""
        # Test QDrant connectivity
        self._test_qdrant_connectivity(config.qdrant, context)

        # Test Neo4j connectivity if configured
        if config.neo4j:
            self._test_neo4j_connectivity(config.neo4j, context)

    def _test_qdrant_connectivity(
        self, qdrant_config, context: DomainValidationContext
    ) -> None:
        """Test actual QDrant database connectivity."""
        try:
            url = qdrant_config.url
            parsed_url = urlparse(url)

            # Test basic network connectivity
            host = parsed_url.hostname
            port = parsed_url.port or (443 if parsed_url.scheme == "https" else 6333)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                context.add_error(
                    message=f"Cannot connect to QDrant at {host}:{port}",
                    field_path="qdrant.url",
                    severity=ValidationSeverity.WARNING,
                    remediation="Ensure QDrant server is running and accessible",
                )
        except Exception as e:
            context.add_error(
                message=f"QDrant connectivity test failed: {str(e)}",
                field_path="qdrant.url",
                severity=ValidationSeverity.WARNING,
                remediation="Check QDrant URL format and network connectivity",
            )

    def _test_neo4j_connectivity(
        self, neo4j_config, context: DomainValidationContext
    ) -> None:
        """Test actual Neo4j database connectivity."""
        try:
            uri = neo4j_config.uri
            parsed_uri = urlparse(uri)

            # Test basic network connectivity
            host = parsed_uri.hostname
            port = parsed_uri.port or 7687

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                context.add_error(
                    message=f"Cannot connect to Neo4j at {host}:{port}",
                    field_path="neo4j.uri",
                    severity=ValidationSeverity.WARNING,
                    remediation="Ensure Neo4j server is running and accessible",
                )
        except Exception as e:
            context.add_error(
                message=f"Neo4j connectivity test failed: {str(e)}",
                field_path="neo4j.uri",
                severity=ValidationSeverity.WARNING,
                remediation="Check Neo4j URI format and network connectivity",
            )
