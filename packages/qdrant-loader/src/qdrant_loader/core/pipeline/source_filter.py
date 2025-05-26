"""Utility for filtering sources based on type and name."""

from qdrant_loader.config import SourcesConfig


class SourceFilter:
    """Utility for filtering sources based on type and name."""

    def filter_sources(
        self,
        sources_config: SourcesConfig,
        source_type: str | None = None,
        source: str | None = None,
    ) -> SourcesConfig:
        """Filter sources based on criteria.

        Args:
            sources_config: The original sources configuration
            source_type: Filter by source type (e.g., 'git', 'confluence')
            source: Filter by specific source name

        Returns:
            Filtered sources configuration
        """
        # If no filters, return original config
        if not source_type and not source:
            return sources_config

        # Create a new config with filtered sources
        filtered_config = SourcesConfig()

        # Filter by source type
        if source_type:
            source_type_lower = source_type.lower()

            if source_type_lower == "git" and sources_config.git:
                filtered_config.git = self._filter_by_name(sources_config.git, source)
            elif source_type_lower == "confluence" and sources_config.confluence:
                filtered_config.confluence = self._filter_by_name(
                    sources_config.confluence, source
                )
            elif source_type_lower == "jira" and sources_config.jira:
                filtered_config.jira = self._filter_by_name(sources_config.jira, source)
            elif source_type_lower == "publicdocs" and sources_config.publicdocs:
                filtered_config.publicdocs = self._filter_by_name(
                    sources_config.publicdocs, source
                )
            elif source_type_lower == "localfile" and sources_config.localfile:
                filtered_config.localfile = self._filter_by_name(
                    sources_config.localfile, source
                )
        else:
            # No source type filter, but filter by name across all types
            if sources_config.git:
                filtered_config.git = self._filter_by_name(sources_config.git, source)
            if sources_config.confluence:
                filtered_config.confluence = self._filter_by_name(
                    sources_config.confluence, source
                )
            if sources_config.jira:
                filtered_config.jira = self._filter_by_name(sources_config.jira, source)
            if sources_config.publicdocs:
                filtered_config.publicdocs = self._filter_by_name(
                    sources_config.publicdocs, source
                )
            if sources_config.localfile:
                filtered_config.localfile = self._filter_by_name(
                    sources_config.localfile, source
                )

        return filtered_config

    def _filter_by_name(self, source_configs: dict, source_name: str | None):
        """Filter source configs by name."""
        if not source_name:
            return source_configs

        # Return only the source with the matching name
        return {
            name: config
            for name, config in source_configs.items()
            if name == source_name
        }
