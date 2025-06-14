"""Source processor for handling different source types."""

import asyncio
from collections.abc import Mapping

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import FileConversionConfig
from qdrant_loader.utils.logging import LoggingConfig

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
        connector_class: type[BaseConnector],
        source_type: str,
    ) -> list[Document]:
        """Process documents from a specific source type.

        Args:
            source_configs: Mapping of source name to source configuration
            connector_class: The connector class to use for this source type
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
                connector = connector_class(source_config)

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

            except Exception as e:
                logger.error(
                    f"Failed to process {source_type} source {source_name}: {e}",
                    exc_info=True,
                )
                # Continue processing other sources even if one fails
                continue

        if all_documents:
            logger.info(
                f"📥 {source_type}: {len(all_documents)} documents from {len(source_configs)} sources"
            )
        return all_documents
