"""Tests for hot-reload configuration functionality."""

import concurrent.futures
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from qdrant_loader.config import (
    ThreadSafeSettingsManager,
    _settings_manager,
    get_settings,
    initialize_multi_file_config,
)
from qdrant_loader.config.hot_reload import HotReloadConfigLoader


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory with sample configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)

        # Create connectivity.yaml
        connectivity_config = {
            "qdrant": {
                "url": "http://localhost:6333",
                "collection_name": "test_collection",
            },
            "embedding": {
                "provider": "openai",
                "model": "test-model",
                "api_key": "test-key",
            },
            "state_management": {"database_path": "/tmp/test.db"},
        }

        with open(config_dir / "connectivity.yaml", "w") as f:
            yaml.dump(connectivity_config, f)

        # Create projects.yaml
        projects_config = {
            "projects": {
                "test-project": {
                    "project_id": "test-project",
                    "display_name": "Test Project",
                    "description": "A test project",
                    "sources": {},
                }
            }
        }

        with open(config_dir / "projects.yaml", "w") as f:
            yaml.dump(projects_config, f)

        # Create fine-tuning.yaml
        fine_tuning_config = {"chunking": {"chunk_size": 1000, "chunk_overlap": 200}}

        with open(config_dir / "fine-tuning.yaml", "w") as f:
            yaml.dump(fine_tuning_config, f)

        yield config_dir


@pytest.fixture
def reset_settings_manager():
    """Reset the settings manager singleton for each test."""
    # Store original instance
    original_instance = ThreadSafeSettingsManager._instance

    # Reset for test
    ThreadSafeSettingsManager._instance = None

    yield

    # Restore original instance
    ThreadSafeSettingsManager._instance = original_instance


class TestThreadSafeSettingsManager:
    """Test thread-safe settings manager functionality."""

    def test_singleton_pattern(self, reset_settings_manager):
        """Test that ThreadSafeSettingsManager follows singleton pattern."""
        manager1 = ThreadSafeSettingsManager.get_instance()
        manager2 = ThreadSafeSettingsManager.get_instance()

        assert manager1 is manager2
        assert isinstance(manager1, ThreadSafeSettingsManager)

    def test_concurrent_singleton_creation(self, reset_settings_manager):
        """Test that singleton creation is thread-safe."""
        instances = []

        def create_instance():
            instances.append(ThreadSafeSettingsManager.get_instance())

        # Create multiple threads trying to create the singleton
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All instances should be the same object
        assert len(instances) == 10
        for instance in instances:
            assert instance is instances[0]

    def test_thread_safe_initialization(self, temp_config_dir, reset_settings_manager):
        """Test that configuration initialization is thread-safe."""
        manager = ThreadSafeSettingsManager.get_instance()
        results = []
        errors = []

        def initialize_config():
            try:
                manager.initialize_multi_file_config(
                    temp_config_dir, enhanced_validation=False
                )
                results.append("success")
            except Exception as e:
                errors.append(str(e))

        # Multiple threads trying to initialize simultaneously
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=initialize_config)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have successful initialization
        assert len(errors) == 0
        assert len(results) == 5
        assert manager.is_initialized()

    def test_concurrent_settings_access(self, temp_config_dir, reset_settings_manager):
        """Test that settings access is thread-safe."""
        # Initialize configuration
        initialize_multi_file_config(temp_config_dir, enhanced_validation=False)

        results = []
        errors = []

        def access_settings():
            try:
                settings = get_settings()
                # Access various properties
                url = settings.qdrant_url
                collection = settings.qdrant_collection_name
                api_key = settings.openai_api_key
                results.append((url, collection, api_key))
            except Exception as e:
                errors.append(str(e))

        # Multiple threads accessing settings concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_settings)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All accesses should succeed
        assert len(errors) == 0
        assert len(results) == 10

        # All results should be identical
        expected = ("http://localhost:6333", "test_collection", "test-key")
        for result in results:
            assert result == expected


class TestHotReloadThreadSafety:
    """Test hot-reload functionality with thread safety."""

    def test_hot_reload_with_concurrent_access(
        self, temp_config_dir, reset_settings_manager
    ):
        """Test that hot-reload works correctly with concurrent configuration access."""
        # Create initial configuration files
        connectivity_file = temp_config_dir / "connectivity.yaml"

        # Initialize hot-reload loader
        loader = HotReloadConfigLoader(update_global_settings=True)
        loader.load_config(
            temp_config_dir, enable_hot_reload=False, skip_validation=True
        )  # Disable file watching for test

        # Track configuration values seen by different threads
        seen_values = set()
        access_errors = []

        def access_config_continuously():
            """Continuously access configuration for a period of time."""
            end_time = time.time() + 1.0  # Run for 1 second
            while time.time() < end_time:
                try:
                    settings = get_settings()
                    collection_name = settings.qdrant_collection_name
                    seen_values.add(collection_name)
                    time.sleep(0.01)  # Small delay
                except Exception as e:
                    access_errors.append(str(e))

        # Start threads that continuously access configuration
        access_threads = []
        for _ in range(3):
            thread = threading.Thread(target=access_config_continuously)
            access_threads.append(thread)
            thread.start()

        # Wait a bit, then simulate configuration update
        time.sleep(0.2)

        # Simulate hot-reload by manually updating settings
        try:
            from qdrant_loader.config import Settings
            from qdrant_loader.config.multi_file_loader import load_multi_file_config

            # Create updated configuration
            updated_connectivity_config = {
                "qdrant": {
                    "url": "http://localhost:6333",
                    "collection_name": "updated_collection",
                },
                "embedding": {
                    "provider": "openai",
                    "model": "test-model",
                    "api_key": "test-key",
                },
                "state_management": {"database_path": "/tmp/test.db"},
            }

            with open(connectivity_file, "w") as f:
                yaml.dump(updated_connectivity_config, f)

            # Load and update settings
            parsed_config = load_multi_file_config(
                temp_config_dir, enhanced_validation=False
            )
            new_settings = Settings(
                global_config=parsed_config.global_config,
                projects_config=parsed_config.projects_config,
            )

            _settings_manager.update_settings(new_settings)

        except Exception as e:
            access_errors.append(f"Update error: {str(e)}")

        # Wait for threads to finish
        for thread in access_threads:
            thread.join()

        # Should have seen both initial and updated values
        assert len(access_errors) == 0
        assert "test_collection" in seen_values
        assert "updated_collection" in seen_values


class TestSettingsPropertyThreadSafety:
    """Test thread-safe property access in Settings class."""

    def test_concurrent_property_access(self, reset_settings_manager):
        """Test that Settings properties can be accessed concurrently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create configuration with Neo4j settings
            connectivity_config = {
                "qdrant": {"url": "http://localhost:6333", "collection_name": "test"},
                "embedding": {
                    "provider": "openai",
                    "api_key": "test-key",
                    "model": "text-embedding-ada-002",
                },
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password": "password",
                    "database": "neo4j",
                },
                "state_management": {"database_path": "/tmp/test.db"},
            }
            projects_config = {
                "projects": {
                    "test-project": {
                        "project_id": "test-project",
                        "display_name": "Test Project",
                        "description": "A test project",
                        "sources": {},
                    }
                }
            }
            fine_tuning_config = {"text_chunking": {"chunk_size": 1000}}

            (config_dir / "connectivity.yaml").write_text(
                yaml.dump(connectivity_config)
            )
            (config_dir / "projects.yaml").write_text(yaml.dump(projects_config))
            (config_dir / "fine-tuning.yaml").write_text(yaml.dump(fine_tuning_config))

            # Initialize configuration
            initialize_multi_file_config(config_dir, enhanced_validation=False)
            settings = get_settings()

            results = []
            errors = []

            def access_all_properties():
                try:
                    # Access all properties
                    props = {
                        "qdrant_url": settings.qdrant_url,
                        "qdrant_collection_name": settings.qdrant_collection_name,
                        "qdrant_api_key": settings.qdrant_api_key,
                        "neo4j_uri": settings.neo4j_uri,
                        "neo4j_user": settings.neo4j_user,
                        "neo4j_password": settings.neo4j_password,
                        "neo4j_database": settings.neo4j_database,
                        "openai_api_key": settings.openai_api_key,
                        "state_db_path": settings.state_db_path,
                    }
                    results.append(props)
                except Exception as e:
                    errors.append(str(e))

            # Multiple threads accessing properties concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(access_all_properties) for _ in range(20)]
                concurrent.futures.wait(futures)

            # All accesses should succeed
            assert len(errors) == 0
            assert len(results) == 20

            # All results should be identical
            expected_props = results[0]
            for props in results:
                assert props == expected_props


def test_hot_reload_loader_basic_functionality(temp_config_dir):
    """Test basic loading functionality without hot-reload."""
    loader = HotReloadConfigLoader()

    # Load configuration without hot-reload
    config = loader.load_config(
        config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
    )

    assert config is not None
    assert loader.get_version() == 1
    assert not loader.is_watching()


def test_hot_reload_loader_with_watching(temp_config_dir):
    """Test loading with file watching enabled."""
    # Skip if watchdog is not available
    try:
        from watchdog.observers import Observer
    except ImportError:
        pytest.skip("watchdog not available")

    loader = HotReloadConfigLoader()

    try:
        # Load configuration with hot-reload
        config = loader.load_config(
            config_dir=temp_config_dir, enable_hot_reload=True, skip_validation=True
        )

        assert config is not None
        assert loader.get_version() == 1
        assert loader.is_watching()

    finally:
        loader.stop_watching()


def test_export_functionality(temp_config_dir):
    """Test configuration export with source attribution."""
    loader = HotReloadConfigLoader()

    # Load configuration
    config = loader.load_config(
        config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
    )

    # Test YAML export
    yaml_export = loader.export_config_with_sources(format="yaml")
    assert isinstance(yaml_export, str)
    assert "configuration:" in yaml_export
    assert "metadata:" in yaml_export

    # Test JSON export
    json_export = loader.export_config_with_sources(format="json")
    assert isinstance(json_export, str)
    json_data = json.loads(json_export)
    assert "configuration" in json_data
    assert "metadata" in json_data

    # Test dict export
    dict_export = loader.export_config_with_sources(format="dict")
    assert isinstance(dict_export, dict)
    assert "configuration" in dict_export
    assert "metadata" in dict_export


def test_export_without_metadata(temp_config_dir):
    """Test configuration export without metadata."""
    loader = HotReloadConfigLoader()

    # Load configuration
    config = loader.load_config(
        config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
    )

    # Export without metadata
    export_data = loader.export_config_with_sources(
        format="dict", include_metadata=False
    )

    assert isinstance(export_data, dict)
    assert "configuration" in export_data
    assert "metadata" not in export_data


def test_context_manager(temp_config_dir):
    """Test using the loader as a context manager."""
    with HotReloadConfigLoader() as loader:
        config = loader.load_config(
            config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
        )
        assert config is not None

    # After context exit, watching should be stopped
    assert not loader.is_watching()


def test_callback_system(temp_config_dir):
    """Test the callback system for configuration changes."""
    loader = HotReloadConfigLoader()

    # Track callback calls
    callback_calls = []

    def test_callback(config):
        callback_calls.append(config)

    # Add callback
    loader.add_reload_callback(test_callback)

    # Load initial configuration
    config = loader.load_config(
        config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
    )

    # Simulate a reload (since we can't easily trigger file changes in tests)
    with patch.object(loader.loader, "load_config") as mock_load:
        mock_load.return_value = config
        loader._reload_config()

    # Check that callback was called
    assert len(callback_calls) == 1

    # Remove callback
    loader.remove_reload_callback(test_callback)

    # Simulate another reload
    with patch.object(loader.loader, "load_config") as mock_load:
        mock_load.return_value = config
        loader._reload_config()

    # Callback should not be called again
    assert len(callback_calls) == 1


def test_version_tracking(temp_config_dir):
    """Test configuration version tracking."""
    loader = HotReloadConfigLoader()

    # Initial version should be 0
    assert loader.get_version() == 0

    # Load configuration
    config = loader.load_config(
        config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
    )

    # Version should increment
    assert loader.get_version() == 1

    # Simulate reload
    with patch.object(loader.loader, "load_config") as mock_load:
        mock_load.return_value = config
        loader._reload_config()

    # Version should increment again
    assert loader.get_version() == 2


def test_error_handling(temp_config_dir):
    """Test error handling in various scenarios."""
    loader = HotReloadConfigLoader()

    # Test export without loaded configuration
    with pytest.raises(RuntimeError, match="No configuration loaded"):
        loader.export_config_with_sources()

    # Test invalid export format
    config = loader.load_config(
        config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
    )

    with pytest.raises(ValueError, match="Unsupported export format"):
        loader.export_config_with_sources(format="invalid")


def test_thread_safety(temp_config_dir):
    """Test thread safety of configuration access."""
    import threading

    loader = HotReloadConfigLoader()
    config = loader.load_config(
        config_dir=temp_config_dir, enable_hot_reload=False, skip_validation=True
    )

    results = []
    errors = []

    def access_config():
        try:
            for _ in range(10):
                current_config = loader.get_config()
                results.append(current_config is not None)
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)

    # Create multiple threads accessing configuration
    threads = [threading.Thread(target=access_config) for _ in range(5)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check results
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert all(results), "Some configuration accesses failed"
    assert len(results) == 50  # 5 threads * 10 accesses each
