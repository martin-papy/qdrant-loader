"""Hot-reload and export functionality for multi-file configuration.

This module provides file watching capabilities for configuration files,
hot-reload support with domain isolation, and export functionality with
source attribution.
"""

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..utils.logging import LoggingConfig
from .models import ParsedConfig
from .multi_file_loader import ConfigDomain, MultiFileConfigLoader

logger = LoggingConfig.get_logger(__name__)


class ConfigFileHandler(FileSystemEventHandler):  # type: ignore
    """File system event handler for configuration files."""

    def __init__(
        self,
        config_files: dict[str, Path],
        reload_callback: Callable[[], None],
        debounce_seconds: float = 1.0,
    ):
        """Initialize the configuration file handler.

        Args:
            config_files: Mapping of domain names to file paths
            reload_callback: Callback function to trigger configuration reload
            debounce_seconds: Minimum time between reload triggers
        """
        super().__init__()
        self.config_files = config_files
        self.reload_callback = reload_callback
        self.debounce_seconds = debounce_seconds
        self.last_reload_time = 0.0
        self._lock = threading.Lock()

        # Create a set of monitored file paths for quick lookup
        self.monitored_paths = {str(path.resolve()) for path in config_files.values()}

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = str(Path(str(event.src_path)).resolve())
        if file_path in self.monitored_paths:
            self._trigger_reload(file_path)

    def on_moved(self, event):
        """Handle file move events."""
        if event.is_directory:
            return

        dest_path = str(Path(str(event.dest_path)).resolve())
        if dest_path in self.monitored_paths:
            self._trigger_reload(dest_path)

    def _trigger_reload(self, file_path: str):
        """Trigger configuration reload with debouncing.

        Args:
            file_path: Path of the modified file
        """
        with self._lock:
            current_time = time.time()
            if current_time - self.last_reload_time >= self.debounce_seconds:
                logger.info(
                    "Configuration file changed, triggering reload", file=file_path
                )
                self.last_reload_time = current_time
                try:
                    self.reload_callback()
                except Exception as e:
                    logger.error("Failed to reload configuration", error=str(e))


class HotReloadConfigLoader:
    """Multi-file configuration loader with hot-reload capabilities."""

    def __init__(self, validator=None, update_global_settings: bool = True):
        """Initialize the hot-reload configuration loader.

        Args:
            validator: Optional configuration validator instance
            update_global_settings: If True, update global settings on reload
        """
        self.loader = MultiFileConfigLoader(validator)
        self._config: ParsedConfig | None = None
        self._config_lock = threading.RLock()
        self._observer: Any | None = None
        self._config_files: dict[str, Path] = {}
        self._config_dir: Path | None = None
        self._domains: set[str] | None = None
        self._env_path: Path | None = None
        self._skip_validation: bool = False
        self._reload_callbacks: list[Callable[[ParsedConfig], None]] = []
        self._version = 0
        self._update_global_settings = update_global_settings

    def load_config(
        self,
        config_dir: Path,
        domains: set[str] | None = None,
        env_path: Path | None = None,
        skip_validation: bool = False,
        enable_hot_reload: bool = True,
    ) -> ParsedConfig:
        """Load configuration with optional hot-reload support.

        Args:
            config_dir: Directory containing configuration files
            domains: Set of domains to load (defaults to all domains)
            env_path: Optional path to .env file
            skip_validation: If True, skip directory validation
            enable_hot_reload: If True, enable file watching for hot-reload

        Returns:
            ParsedConfig: Loaded configuration

        Raises:
            FileNotFoundError: If required configuration files are missing
            ValidationError: If configuration validation fails
        """
        with self._config_lock:
            # Store parameters for reload operations
            self._config_dir = config_dir
            self._domains = domains or ConfigDomain.ALL_DOMAINS.copy()
            self._env_path = env_path
            self._skip_validation = skip_validation

            # Recreate loader with appropriate validation settings if needed
            if skip_validation and self.loader.enhanced_validation:
                self.loader = MultiFileConfigLoader(
                    validator=self.loader.validator,
                    enhanced_validation=False,
                )

            # Load initial configuration
            self._config = self.loader.load_config(
                config_dir=config_dir,
                domains=domains,
                env_path=env_path,
                skip_validation=skip_validation,
            )
            self._version += 1

            # Update global settings if enabled
            if self._update_global_settings:
                self._update_global_settings_instance()

            # Set up hot-reload if enabled
            if enable_hot_reload:
                self._setup_file_watching()

            logger.info(
                "Configuration loaded successfully",
                version=self._version,
                hot_reload_enabled=enable_hot_reload,
                global_settings_update=self._update_global_settings,
            )

            return self._config

    def _update_global_settings_instance(self):
        """Update the global settings instance with the current configuration."""
        if self._config is None:
            return

        try:
            # Import here to avoid circular imports
            from . import Settings, _settings_manager

            # Create new Settings instance from parsed config
            new_settings = Settings(
                global_config=self._config.global_config,
                projects_config=self._config.projects_config,
            )

            # Update global settings manager
            _settings_manager.update_settings(new_settings)

            logger.debug("Global settings updated from hot-reload")

        except Exception as e:
            logger.error(
                "Failed to update global settings from hot-reload", error=str(e)
            )

    def get_config(self) -> ParsedConfig | None:
        """Get the current configuration thread-safely.

        Returns:
            Current configuration or None if not loaded
        """
        with self._config_lock:
            return self._config

    def add_reload_callback(self, callback: Callable[[ParsedConfig], None]):
        """Add a callback to be called when configuration is reloaded.

        Args:
            callback: Function to call with the new configuration
        """
        with self._config_lock:
            self._reload_callbacks.append(callback)

    def remove_reload_callback(self, callback: Callable[[ParsedConfig], None]):
        """Remove a reload callback.

        Args:
            callback: Function to remove from callbacks
        """
        with self._config_lock:
            if callback in self._reload_callbacks:
                self._reload_callbacks.remove(callback)

    def _setup_file_watching(self):
        """Set up file system watching for configuration files."""
        if not self._config_dir:
            return

        # Discover configuration files
        self._config_files = self.loader._discover_config_files(
            self._config_dir, self._domains or set()
        )

        if not self._config_files:
            logger.warning("No configuration files found for watching")
            return

        # Set up file system observer
        try:
            self._observer = Observer()
            handler = ConfigFileHandler(
                config_files=self._config_files,
                reload_callback=self._reload_config,
                debounce_seconds=1.0,
            )

            # Watch the configuration directory
            self._observer.schedule(handler, str(self._config_dir), recursive=False)
            self._observer.start()

            logger.info(
                "File watching started",
                config_dir=str(self._config_dir),
                watched_files=list(self._config_files.keys()),
            )

        except Exception as e:
            logger.error("Failed to start file watching", error=str(e))
            self._observer = None

    def _reload_config(self):
        """Reload configuration from files."""
        if not self._config_dir:
            logger.warning("Cannot reload: configuration directory not set")
            return

        with self._config_lock:
            try:
                logger.info("Reloading configuration from files")

                # Reload configuration
                new_config = self.loader.load_config(
                    config_dir=self._config_dir,
                    domains=self._domains,
                    env_path=self._env_path,
                    skip_validation=self._skip_validation,
                )

                # Atomic update
                old_version = self._version
                self._config = new_config
                self._version += 1

                # Update global settings if enabled
                if self._update_global_settings:
                    self._update_global_settings_instance()

                logger.info(
                    "Configuration reloaded successfully",
                    old_version=old_version,
                    new_version=self._version,
                )

                # Notify callbacks
                for callback in self._reload_callbacks:
                    try:
                        callback(new_config)
                    except Exception as e:
                        logger.error("Reload callback failed", error=str(e))

            except Exception as e:
                logger.error("Failed to reload configuration", error=str(e))

    def export_config_with_sources(
        self, format: str = "yaml", include_metadata: bool = True
    ) -> str | dict[str, Any]:
        """Export current configuration with source attribution.

        Args:
            format: Export format ('yaml', 'json', or 'dict')
            include_metadata: If True, include metadata about sources and version

        Returns:
            Exported configuration as string or dictionary

        Raises:
            ValueError: If format is not supported
            RuntimeError: If no configuration is loaded
        """
        with self._config_lock:
            if not self._config:
                raise RuntimeError("No configuration loaded")

            # Build export data with source attribution
            export_data = self._build_export_data(include_metadata)

            if format.lower() == "dict":
                return export_data
            elif format.lower() == "json":
                return json.dumps(export_data, indent=2, default=str)
            elif format.lower() == "yaml":
                return yaml.dump(export_data, default_flow_style=False, sort_keys=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")

    def _build_export_data(self, include_metadata: bool) -> dict[str, Any]:
        """Build export data with source attribution.

        Args:
            include_metadata: If True, include metadata

        Returns:
            Dictionary with configuration and source information
        """
        if not self._config:
            return {}

        # Convert configuration to dictionary
        config_dict = {}
        if hasattr(self._config, "global_config") and hasattr(
            self._config, "projects_config"
        ):
            # Handle ParsedConfig structure
            if hasattr(self._config.global_config, "model_dump"):
                config_dict.update(self._config.global_config.model_dump())
            elif hasattr(self._config.global_config, "__dict__"):
                config_dict.update(vars(self._config.global_config))

            if hasattr(self._config.projects_config, "to_dict"):
                config_dict.update(self._config.projects_config.to_dict())
            elif hasattr(self._config.projects_config, "model_dump"):
                config_dict.update(self._config.projects_config.model_dump())
        elif hasattr(self._config, "__dict__"):
            config_dict = vars(self._config)

        export_data = {
            "configuration": config_dict,
        }

        if include_metadata:
            export_data["metadata"] = {
                "version": self._version,
                "domains": list(self._domains) if self._domains else [],
                "config_files": {
                    domain: str(path) for domain, path in self._config_files.items()
                },
                "hot_reload_enabled": self._observer is not None,
                "last_reload_time": time.time(),
            }

            # Add source attribution for major configuration sections
            source_attribution = {}
            for domain, file_path in self._config_files.items():
                if domain == ConfigDomain.CONNECTIVITY:
                    sections = [
                        "qdrant",
                        "embedding",
                        "neo4j",
                        "graphiti",
                        "state_management",
                    ]
                elif domain == ConfigDomain.PROJECTS:
                    sections = ["projects"]
                elif domain == ConfigDomain.FINE_TUNING:
                    sections = ["chunking", "file_conversion"]
                else:
                    sections = []

                for section in sections:
                    if section in config_dict:
                        source_attribution[section] = {
                            "source_file": str(file_path),
                            "domain": domain,
                        }

            export_data["metadata"]["source_attribution"] = source_attribution

        return export_data

    def stop_watching(self):
        """Stop file watching and clean up resources."""
        with self._config_lock:
            if self._observer:
                logger.info("Stopping configuration file watching")
                self._observer.stop()
                self._observer.join(timeout=5.0)
                self._observer = None

    def get_version(self) -> int:
        """Get the current configuration version.

        Returns:
            Configuration version number
        """
        with self._config_lock:
            return self._version

    def is_watching(self) -> bool:
        """Check if file watching is active.

        Returns:
            True if file watching is active
        """
        with self._config_lock:
            return self._observer is not None and self._observer.is_alive()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop_watching()
