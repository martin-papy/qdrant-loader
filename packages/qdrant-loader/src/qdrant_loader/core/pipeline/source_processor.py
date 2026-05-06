"""Source processor for handling different source types."""

import asyncio
from collections.abc import Callable, Mapping

from qdrant_loader import connectors
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.connectors.base import BaseConnector, ConnectorConfigurationError
from qdrant_loader.connectors.factory import get_connector_instance
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import FileConversionConfig
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.utils.sensitive import sanitize_exception_message

logger = LoggingConfig.get_logger(__name__)


class SourceProcessor:
    """Handles processing of different source types."""

    def __init__(
        self,
        shutdown_event: asyncio.Event | None = None,
        file_conversion_config: FileConversionConfig | None = None,
    ):
        self.shutdown_event = shutdown_event or asyncio.Event()
        self.file_conversion_config = file_conversion_config

    async def process_source_type(
        self,
        source_configs: Mapping[str, SourceConfig],
        connector_factory: Callable[[SourceConfig], BaseConnector],
        source_type: str,
    ) -> list[Document]:
        """Process documents from a specific source type.

        Args:
            source_configs: Mapping of source name to source configuration
            connector_factory: Factory function that creates a connector from a source config
            source_type: The type of source being processed

        Returns:
            List of documents from all sources of this type
        """
        logger.debug(f"Processing {source_type} sources: {list(source_configs.keys())}")

        all_documents = []

        for source_name, source_config in source_configs.items():
            if self.shutdown_event.is_set():
                logger.info(
                    f"Shutdown requested, skipping {source_type} source: {source_name}"
                )
                break

            try:
                logger.debug(f"Processing {source_type} source: {source_name}")

                # Create connector instance and use as async context manager
                connector = connector_factory(source_config)

                # Set file conversion config if available and connector supports it
                if (
                    self.file_conversion_config
                    and hasattr(connector, "set_file_conversion_config")
                    and hasattr(source_config, "enable_file_conversion")
                    and source_config.enable_file_conversion
                ):
                    logger.debug(
                        f"Setting file conversion config for {source_type} source: {source_name}"
                    )
                    connector.set_file_conversion_config(self.file_conversion_config)

                # Use the connector as an async context manager to ensure proper initialization
                async with connector:
                    # Get documents from this source
                    documents = await connector.get_documents()

                    logger.debug(
                        f"Retrieved {len(documents)} documents from {source_type} source: {source_name}"
                    )
                    all_documents.extend(documents)

            except ConnectorConfigurationError:
                # Fatal configuration error – re-raise immediately so the
                # pipeline stops with a clear message instead of silently
                # producing 0 documents.
                raise
            except Exception as e:
                safe_error = sanitize_exception_message(e)
                logger.error(
                    f"Failed to process {source_type} source {source_name}: {safe_error}",
                    error_type=type(e).__name__,
                )
                # Continue processing other sources even if one fails
                continue

        if all_documents:
            logger.info(
                f"📥 {source_type}: {len(all_documents)} documents from {len(source_configs)} sources"
            )
        return all_documents

    async def get_sources(
        self,
        filtered_config: SourcesConfig,
    ) -> list[BaseConnector]:
        """
        Create and return all connectors (No document fetching).
        """
        connectors: list[BaseConnector] = []

        def _prepare_connector(connector, source_config):
            if(
                self.file_conversion_config
                and hasattr(connector, "set_file_conversion_config")
                and hasattr(source_config, "enable_file_conversion")
                and source_config.enable_file_conversion
            ):
                connector.set_file_conversion_config(self.file_conversion_config)
            return connector
        
        source_groups = {
            "jira": filtered_config.jira,
            "confluence": filtered_config.confluence,
            "git": filtered_config.git,
            "localfile": filtered_config.localfile,
            "publicdocs": filtered_config.publicdocs,
        }

        for source_type, sources in source_groups.items():
            if not sources:
                continue
            for source_name, source_config in sources.items():
                try:
                    connector = get_connector_instance(source_config)
                    connectors.append(_prepare_connector(connector, source_config))

                    logger.debug(
                        "Connector created",
                        source_type=source_type,
                        source_name=source_name,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create connector for {source_type} source {source_name}: {sanitize_exception_message(e)}",
                        error_type=type(e).__name__,
                    )
                    continue
        return connectors
