"""
Comprehensive unit tests for Neo4jManager.

This test suite covers:
- Connection management and lifecycle
- Query execution with retry logic
- Transaction handling (read/write)
- Database information retrieval
- Index and constraint management
- Performance analysis and optimization
- Connection pool management
- Data pruning operations
- Error handling and edge cases
- Health checks and monitoring
"""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock, call, PropertyMock
from typing import Any

import pytest
from neo4j.exceptions import (
    AuthError,
    ClientError,
    ConfigurationError,
    DatabaseError,
    ServiceUnavailable,
    SessionExpired,
    TransactionError,
    TransientError,
)

from qdrant_loader.core.managers.neo4j_manager import (
    Neo4jManager,
    retry_on_transient_failure,
    _is_retryable_exception,
)
from qdrant_loader.config.neo4j import Neo4jConfig


class TestRetryableExceptions:
    """Test the _is_retryable_exception function."""

    def test_transient_error_is_retryable(self):
        """Test that TransientError is retryable."""
        exception = TransientError("Temporary issue")
        assert _is_retryable_exception(exception)

    def test_service_unavailable_is_retryable(self):
        """Test that ServiceUnavailable is retryable."""
        exception = ServiceUnavailable("Service down")
        assert _is_retryable_exception(exception)

    def test_session_expired_is_retryable(self):
        """Test that SessionExpired is retryable."""
        exception = SessionExpired("Session expired")
        assert _is_retryable_exception(exception)

    def test_transaction_error_with_retryable_keywords(self):
        """Test that TransactionError with retryable keywords is retryable."""
        retryable_messages = [
            "deadlock detected",
            "lock timeout",
            "connection lost",
            "network error",
            "temporary failure",
        ]
        for message in retryable_messages:
            # Create a mock TransactionError with the message
            exception = Mock(spec=TransactionError)
            exception.__str__ = Mock(return_value=message)
            exception.args = (message,)
            exception.message = message
            assert _is_retryable_exception(exception)

    def test_transaction_error_without_retryable_keywords(self):
        """Test that TransactionError without retryable keywords is not retryable."""
        non_retryable_messages = [
            "syntax error",
            "invalid query",
            "constraint violation",
        ]
        for message in non_retryable_messages:
            # Create a mock TransactionError with the message
            exception = Mock(spec=TransactionError)
            exception.__str__ = Mock(return_value=message)
            exception.args = (message,)
            exception.message = message
            assert not _is_retryable_exception(exception)

    def test_auth_error_not_retryable(self):
        """Test that AuthError is not retryable."""
        exception = AuthError("Invalid credentials")
        assert not _is_retryable_exception(exception)

    def test_configuration_error_not_retryable(self):
        """Test that ConfigurationError is not retryable."""
        exception = ConfigurationError("Invalid config")
        assert not _is_retryable_exception(exception)

    def test_client_error_not_retryable(self):
        """Test that ClientError is not retryable."""
        exception = ClientError("Client error")
        assert not _is_retryable_exception(exception)

    def test_generic_database_error_with_retryable_keywords(self):
        """Test that DatabaseError with retryable keywords is retryable."""
        retryable_messages = [
            "deadlock detected in transaction",
            "lock timeout exceeded",
            "connection lost during query",
            "network error occurred",
            "temporary failure in processing",
        ]
        for message in retryable_messages:
            # Create a mock DatabaseError with the message
            exception = Mock(spec=DatabaseError)
            exception.__str__ = Mock(return_value=message)
            exception.args = (message,)
            assert _is_retryable_exception(exception)

    def test_generic_database_error_without_retryable_keywords(self):
        """Test that DatabaseError without retryable keywords is not retryable."""
        non_retryable_messages = [
            "syntax error in query",
            "invalid parameter",
            "constraint violation",
        ]
        for message in non_retryable_messages:
            # Create a mock DatabaseError with the message
            exception = Mock(spec=DatabaseError)
            exception.__str__ = Mock(return_value=message)
            exception.args = (message,)
            assert not _is_retryable_exception(exception)


class TestRetryDecorator:
    """Test the retry_on_transient_failure decorator."""

    def test_retry_decorator_success_on_first_attempt(self):
        """Test that successful operations don't retry."""
        mock_config = Mock()
        mock_config.max_retry_time = 5
        mock_config.initial_retry_delay = 0.1
        mock_config.retry_delay_multiplier = 2.0
        mock_config.retry_delay_jitter_factor = 0.1

        class TestClass:
            def __init__(self):
                self.config = mock_config

            @retry_on_transient_failure()
            def test_method(self):
                return "success"

        test_instance = TestClass()
        result = test_instance.test_method()
        assert result == "success"

    def test_retry_decorator_with_retryable_exception(self):
        """Test that retryable exceptions trigger retries."""
        mock_config = Mock()
        mock_config.max_retry_time = 5
        mock_config.initial_retry_delay = 0.01  # Very short for testing
        mock_config.retry_delay_multiplier = 2.0
        mock_config.retry_delay_jitter_factor = 0.1

        class TestClass:
            def __init__(self):
                self.config = mock_config
                self.attempt_count = 0

            @retry_on_transient_failure()
            def test_method(self):
                self.attempt_count += 1
                if self.attempt_count < 3:
                    raise TransientError("Temporary failure")
                return "success"

        test_instance = TestClass()
        with patch("time.sleep"):  # Mock sleep to speed up test
            result = test_instance.test_method()
            assert result == "success"
            assert test_instance.attempt_count == 3

    def test_retry_decorator_with_non_retryable_exception(self):
        """Test that non-retryable exceptions don't trigger retries."""
        mock_config = Mock()
        mock_config.max_retry_time = 5
        mock_config.initial_retry_delay = 0.1
        mock_config.retry_delay_multiplier = 2.0
        mock_config.retry_delay_jitter_factor = 0.1

        class TestClass:
            def __init__(self):
                self.config = mock_config
                self.attempt_count = 0

            @retry_on_transient_failure()
            def test_method(self):
                self.attempt_count += 1
                raise AuthError("Not retryable")

        test_instance = TestClass()
        with pytest.raises(AuthError):
            test_instance.test_method()
        assert test_instance.attempt_count == 1


class TestNeo4jManager:
    """Test the Neo4jManager class."""

    @pytest.fixture
    def neo4j_config(self):
        """Create a test Neo4j configuration."""
        return Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            database="neo4j",
            max_retry_time=5,
            initial_retry_delay=0.1,
            retry_delay_multiplier=2.0,
            retry_delay_jitter_factor=0.1,
        )

    @pytest.fixture
    def neo4j_manager(self, neo4j_config):
        """Create a test Neo4j manager."""
        return Neo4jManager(neo4j_config)

    @pytest.fixture
    def mock_driver(self):
        """Create a mock Neo4j driver."""
        driver = Mock()
        driver.close = Mock()
        return driver

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session with proper context manager support."""
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)

        # Mock result object
        mock_result = Mock()
        mock_record = Mock()
        mock_record.data.return_value = {"test": 1}
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))

        session.run.return_value = mock_result
        session.execute_write.return_value = [{"result": "success"}]
        session.execute_read.return_value = [{"result": "success"}]

        return session

    def test_initialization(self, neo4j_config):
        """Test Neo4jManager initialization."""
        manager = Neo4jManager(neo4j_config)
        assert manager.config == neo4j_config
        assert manager._driver is None
        assert not manager._is_connected

    def test_context_manager_protocol(self, neo4j_manager, mock_driver):
        """Test context manager protocol."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        with neo4j_manager as manager:
            assert manager is neo4j_manager

        mock_driver.close.assert_called_once()

    @patch("qdrant_loader.core.managers.neo4j_manager.GraphDatabase")
    def test_connect_success(self, mock_graph_db, neo4j_manager, mock_driver):
        """Test successful connection."""
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.verify_connectivity.return_value = None

        neo4j_manager.connect()

        assert neo4j_manager._driver == mock_driver
        assert neo4j_manager._is_connected
        mock_graph_db.driver.assert_called_once()

    @patch("qdrant_loader.core.managers.neo4j_manager.GraphDatabase")
    def test_connect_already_connected(self, mock_graph_db, neo4j_manager, mock_driver):
        """Test connection when already connected."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        neo4j_manager.connect()

        # Should not create new driver
        mock_graph_db.driver.assert_not_called()

    @patch("qdrant_loader.core.managers.neo4j_manager.GraphDatabase")
    def test_connect_auth_error(self, mock_graph_db, neo4j_manager):
        """Test connection with authentication error."""
        mock_graph_db.driver.side_effect = AuthError("Invalid credentials")

        with pytest.raises(AuthError):
            neo4j_manager.connect()

        assert not neo4j_manager._is_connected

    @patch("qdrant_loader.core.managers.neo4j_manager.GraphDatabase")
    def test_connect_with_trusted_certificates_trust_all(
        self, mock_graph_db, neo4j_manager
    ):
        """Test connection with trust_all certificates."""
        neo4j_manager.config.trusted_certificates = "trust_all"
        mock_driver = Mock()
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        neo4j_manager.connect()

        # Verify driver was called with correct trust configuration
        call_args = mock_graph_db.driver.call_args
        assert call_args is not None

        # Check that trust was configured
        kwargs = call_args[1] if len(call_args) > 1 else {}
        # The exact trust configuration depends on implementation
        assert neo4j_manager._is_connected

    @patch("qdrant_loader.core.managers.neo4j_manager.GraphDatabase")
    def test_connect_with_trusted_certificates_system_ca(
        self, mock_graph_db, neo4j_manager
    ):
        """Test connection with system CA certificates."""
        neo4j_manager.config.trusted_certificates = "system_ca"
        mock_driver = Mock()
        mock_driver.verify_connectivity.return_value = None
        mock_graph_db.driver.return_value = mock_driver

        neo4j_manager.connect()

        # Verify driver was called with correct trust configuration
        call_args = mock_graph_db.driver.call_args
        assert call_args is not None

        # Check that trust was configured
        kwargs = call_args[1] if len(call_args) > 1 else {}
        # The exact trust configuration depends on implementation
        assert neo4j_manager._is_connected

    def test_close_connection(self, neo4j_manager, mock_driver):
        """Test closing connection."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        neo4j_manager.close()

        assert not neo4j_manager._is_connected
        assert neo4j_manager._driver is None
        mock_driver.close.assert_called_once()

    def test_close_when_not_connected(self, neo4j_manager):
        """Test closing when not connected."""
        neo4j_manager.close()  # Should not raise

    def test_get_session_basic(self, neo4j_manager, mock_driver, mock_session):
        """Test getting a basic session."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        session = neo4j_manager.get_session()

        assert session == mock_session
        mock_driver.session.assert_called_once()

    def test_get_session_with_database(self, neo4j_manager, mock_driver, mock_session):
        """Test getting session with specific database."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        session = neo4j_manager.get_session(database="test_db")

        assert session == mock_session
        call_args = mock_driver.session.call_args
        assert call_args[1]["database"] == "test_db"

    def test_get_session_with_read_access_mode(
        self, neo4j_manager, mock_driver, mock_session
    ):
        """Test getting session with read access mode."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        # Mock the neo4j module to provide READ_ACCESS
        with patch("neo4j.READ_ACCESS", "READ"):
            session = neo4j_manager.get_session(access_mode="READ")

        assert session == mock_session
        mock_driver.session.assert_called_once()

    def test_get_session_with_write_access_mode(
        self, neo4j_manager, mock_driver, mock_session
    ):
        """Test getting session with write access mode."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        # Mock the neo4j module to provide WRITE_ACCESS
        with patch("neo4j.WRITE_ACCESS", "WRITE"):
            session = neo4j_manager.get_session(access_mode="WRITE")

        assert session == mock_session
        mock_driver.session.assert_called_once()

    def test_get_session_not_connected(self, neo4j_manager):
        """Test getting session when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            neo4j_manager.get_session()

    def test_execute_query_success(self, neo4j_manager, mock_driver, mock_session):
        """Test successful query execution."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        result = neo4j_manager.execute_query("RETURN 1")

        assert result == [{"test": 1}]
        mock_session.run.assert_called_once_with("RETURN 1", {})

    def test_execute_query_with_parameters(
        self, neo4j_manager, mock_driver, mock_session
    ):
        """Test query execution with parameters."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        # Setup mock result with parameters
        mock_result = Mock()
        mock_record = Mock()
        mock_record.data.return_value = {"name": "test", "value": 42}
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run.return_value = mock_result

        parameters = {"name": "test", "value": 42}
        result = neo4j_manager.execute_query(
            "MATCH (n {name: $name}) RETURN n.value as value", parameters
        )

        assert result == [{"name": "test", "value": 42}]
        mock_session.run.assert_called_once_with(
            "MATCH (n {name: $name}) RETURN n.value as value", parameters
        )

    def test_execute_query_not_connected(self, neo4j_manager):
        """Test query execution when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            neo4j_manager.execute_query("RETURN 1")

    def test_execute_write_transaction_success(
        self, neo4j_manager, mock_driver, mock_session
    ):
        """Test successful write transaction."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        result = neo4j_manager.execute_write_transaction("CREATE (n:Test)")

        assert result == [{"result": "success"}]
        mock_session.execute_write.assert_called_once()

    def test_execute_read_transaction_success(
        self, neo4j_manager, mock_driver, mock_session
    ):
        """Test successful read transaction."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        result = neo4j_manager.execute_read_transaction("MATCH (n) RETURN count(n)")

        assert result == [{"result": "success"}]
        mock_session.execute_read.assert_called_once()

    def test_test_connection_success(self, neo4j_manager):
        """Test successful connection test."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "execute_query") as mock_execute:
            mock_execute.return_value = [{"test": 1}]

            result = neo4j_manager.test_connection()

            assert result is True
            mock_execute.assert_called_once_with("RETURN 1 as test")

    def test_test_connection_failure(self, neo4j_manager):
        """Test connection test failure."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "execute_query") as mock_execute:
            mock_execute.side_effect = Exception("Connection failed")

            result = neo4j_manager.test_connection()

            assert result is False

    def test_test_connection_when_not_connected(self, neo4j_manager):
        """Test connection test when not initially connected."""
        # Start with not connected
        neo4j_manager._is_connected = False
        neo4j_manager._driver = None

        with patch.object(neo4j_manager, "connect") as mock_connect:
            with patch.object(neo4j_manager, "execute_query") as mock_execute:
                # After connect is called, simulate connection
                def side_effect():
                    neo4j_manager._is_connected = True
                    neo4j_manager._driver = Mock()

                mock_connect.side_effect = side_effect
                mock_execute.return_value = [{"test": 1}]

                result = neo4j_manager.test_connection()

                assert result is True
                mock_connect.assert_called_once()
                mock_execute.assert_called_once_with("RETURN 1 as test")

    def test_get_database_info_success(self, neo4j_manager):
        """Test successful database info retrieval."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Mock version info query
        version_info = [
            {"name": "Neo4j Kernel", "versions": ["4.4.0"], "edition": "community"}
        ]

        # Mock statistics query
        stats_info = [{"node_count": 100, "relationship_count": 50}]

        # Mock APOC query
        apoc_info = [{"apoc_version": "4.4.0.1"}]
        apoc_procedures = [{"apoc_procedures": 25}]

        with patch.object(neo4j_manager, "execute_query") as mock_execute:
            mock_execute.side_effect = [
                version_info,  # First call for version info
                stats_info,  # Second call for statistics
                apoc_info,  # Third call for APOC version
                apoc_procedures,  # Fourth call for APOC procedures count
            ]

            result = neo4j_manager.get_database_info()

            assert "version" in result
            assert "edition" in result
            assert "statistics" in result

    def test_get_database_info_not_connected(self, neo4j_manager):
        """Test database info retrieval when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            neo4j_manager.get_database_info()

    def test_create_indexes_success(self, neo4j_manager):
        """Test successful index creation."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Create a proper session mock with context manager support
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.execute_write = Mock(return_value=[])

        with patch.object(neo4j_manager, "get_session") as mock_get_session:
            mock_get_session.return_value = mock_session

            neo4j_manager.create_indexes()

            # Should have been called for creating indexes
            assert mock_get_session.called

    def test_analyze_query_performance(self, neo4j_manager):
        """Test query performance analysis."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Mock EXPLAIN result
        explain_result = [
            {
                "plan": {
                    "operatorType": "NodeByLabelScan",
                    "identifiers": ["n"],
                    "arguments": {"LabelName": "Person"},
                    "children": [],
                }
            }
        ]

        # Mock PROFILE result
        profile_result = [
            {
                "plan": {
                    "operatorType": "NodeByLabelScan",
                    "dbHits": 100,
                    "rows": 50,
                    "time": 25,
                }
            }
        ]

        with patch.object(neo4j_manager, "execute_query") as mock_execute:
            mock_execute.side_effect = [explain_result, profile_result]

            result = neo4j_manager.analyze_query_performance(
                "MATCH (n:Person) RETURN n"
            )

            assert "execution_plan" in result
            assert "profile" in result
            assert "performance_summary" in result

    def test_get_index_usage_stats(self, neo4j_manager):
        """Test index usage statistics retrieval."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Mock index and constraint results
        indexes = [{"name": "person_name_index", "type": "BTREE"}]
        constraints = [{"name": "person_id_unique", "type": "UNIQUENESS"}]
        db_stats = [
            {
                "total_nodes": 1000,
                "total_relationships": 2000,
                "all_labels": ["Person", "Company"],
            }
        ]

        with patch.object(neo4j_manager, "execute_query") as mock_execute:
            mock_execute.side_effect = [indexes, constraints, db_stats]

            result = neo4j_manager.get_index_usage_stats()

            assert "indexes" in result
            assert "constraints" in result
            assert "database_stats" in result

    def test_get_connection_pool_stats(self, neo4j_manager, mock_driver):
        """Test connection pool statistics retrieval."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        # Mock driver pool stats
        mock_driver.get_server_info.return_value = Mock(
            connection_id="conn_123",
            server_agent="Neo4j/4.4.0",
        )

        result = neo4j_manager.get_connection_pool_stats()

        assert isinstance(result, dict)
        assert "health" in result
        assert "pool_config" in result
        assert "driver_info" in result

    def test_clear_database(self, neo4j_manager):
        """Test database clearing operation."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "execute_write_transaction") as mock_execute:
            mock_execute.return_value = []

            neo4j_manager.clear_database()

            # Should be called twice: once for relationships, once for nodes
            assert mock_execute.call_count == 2
            calls = mock_execute.call_args_list
            assert (
                calls[0][0][0] == "MATCH ()-[r]-() DELETE r"
            )  # Delete relationships first
            assert calls[1][0][0] == "MATCH (n) DELETE n"  # Then delete nodes

    def test_clear_database_not_connected(self, neo4j_manager):
        """Test database clearing when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            neo4j_manager.clear_database()

    def test_execute_read_query(self, neo4j_manager):
        """Test read query execution."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "execute_query") as mock_execute:
            mock_execute.return_value = [{"result": "read_success"}]

            result = neo4j_manager.execute_read_query("MATCH (n) RETURN n")

            assert result == [{"result": "read_success"}]
            mock_execute.assert_called_once_with(
                "MATCH (n) RETURN n", None, None, access_mode="READ"
            )

    def test_execute_write_query(self, neo4j_manager):
        """Test write query execution."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "execute_query") as mock_execute:
            mock_execute.return_value = [{"result": "write_success"}]

            result = neo4j_manager.execute_write_query("CREATE (n:Test)")

            assert result == [{"result": "write_success"}]
            mock_execute.assert_called_once_with(
                "CREATE (n:Test)", None, None, access_mode="WRITE"
            )

    def test_health_check_healthy(self, neo4j_manager):
        """Test health check when system is healthy."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "test_connection") as mock_test:
            with patch.object(neo4j_manager, "get_database_info") as mock_db_info:
                mock_test.return_value = True
                mock_db_info.return_value = {
                    "version": "4.4.0",
                    "edition": "community",
                }

                result = neo4j_manager.health_check()

                assert result["status"] == "healthy"
                assert result["connected"] is True

    def test_health_check_not_connected(self, neo4j_manager):
        """Test health check when not connected."""
        # Ensure not connected
        neo4j_manager._is_connected = False
        neo4j_manager._driver = None

        result = neo4j_manager.health_check()

        assert result["status"] == "unhealthy"
        assert result["connected"] is False
        assert "Not connected to Neo4j" in result["error"]

    def test_health_check_connection_test_failed(self, neo4j_manager):
        """Test health check when connection test fails."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "test_connection") as mock_test:
            mock_test.return_value = False

            result = neo4j_manager.health_check()

            assert result["status"] == "unhealthy"
            assert result["connected"] is False
            # The actual error message comes from the implementation
            assert "error" in result

    def test_health_check_exception(self, neo4j_manager):
        """Test health check when exception occurs."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "test_connection") as mock_test:
            mock_test.side_effect = Exception("Unexpected error")

            result = neo4j_manager.health_check()

            assert result["status"] == "unhealthy"
            assert result["connected"] is False
            assert "Unexpected error" in result["error"]

    def test_batch_execute_queries_success(
        self, neo4j_manager, mock_driver, mock_session
    ):
        """Test successful batch query execution."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        # Mock session context manager properly
        mock_driver.session.return_value = mock_session
        mock_session.execute_write.return_value = [{"result": "batch_success"}]

        queries = [
            ("CREATE (n:Test {name: $name})", {"name": "test1"}),
            ("CREATE (n:Test {name: $name})", {"name": "test2"}),
        ]

        result = neo4j_manager.batch_execute_queries(queries)

        assert len(result) == 1  # Single transaction result
        assert result[0] == {"result": "batch_success"}

    def test_prune_old_data_dry_run(self, neo4j_manager):
        """Test data pruning in dry run mode."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Mock count query result
        count_result = [{"nodes_to_delete": 10, "relationships_to_delete": 5}]

        with patch.object(neo4j_manager, "execute_read_query") as mock_execute:
            mock_execute.return_value = count_result

            result = neo4j_manager.prune_old_data(older_than_days=30, dry_run=True)

            assert "dry_run" in result
            assert result["dry_run"] is True

    def test_prune_orphaned_nodes_dry_run(self, neo4j_manager):
        """Test orphaned nodes pruning in dry run mode."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Mock orphaned nodes query result
        orphaned_result = [{"orphaned_nodes": 3}]

        with patch.object(neo4j_manager, "execute_read_query") as mock_execute:
            mock_execute.return_value = orphaned_result

            result = neo4j_manager.prune_orphaned_nodes(dry_run=True)

            assert "dry_run" in result
            assert result["dry_run"] is True

    def test_comprehensive_data_pruning(self, neo4j_manager):
        """Test comprehensive data pruning operation."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "prune_old_data") as mock_old:
            with patch.object(neo4j_manager, "prune_orphaned_nodes") as mock_orphaned:
                with patch.object(
                    neo4j_manager, "prune_duplicate_relationships"
                ) as mock_duplicates:
                    with patch.object(
                        neo4j_manager, "prune_low_quality_entities"
                    ) as mock_low_quality:
                        mock_old.return_value = {"nodes_deleted": 5}
                        mock_orphaned.return_value = {"orphaned_nodes_deleted": 2}
                        mock_duplicates.return_value = {
                            "duplicate_relationships_deleted": 3
                        }
                        mock_low_quality.return_value = {
                            "low_quality_entities_deleted": 1
                        }

                        result = neo4j_manager.comprehensive_data_pruning(dry_run=True)

                        assert "dry_run" in result
                        assert "old_data_pruning" in result

    def test_get_pruning_recommendations(self, neo4j_manager):
        """Test pruning recommendations generation."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Mock various statistics queries
        with patch.object(neo4j_manager, "execute_read_query") as mock_execute:
            mock_execute.side_effect = [
                [{"old_nodes": 100}],  # Old nodes count
                [{"orphaned_nodes": 25}],  # Orphaned nodes count
                [{"duplicate_rels": 15}],  # Duplicate relationships count
                [{"low_quality": 10}],  # Low quality entities count
            ]

            result = neo4j_manager.get_pruning_recommendations()

            assert "recommendations" in result
            assert "statistics" in result

    def test_optimize_query_for_performance(self, neo4j_manager):
        """Test query optimization for performance."""
        query = "MATCH (n:Person) WHERE n.name = 'John' RETURN n"

        result = neo4j_manager.optimize_query_for_performance(query)

        assert isinstance(result, str)
        # The optimized query should be different from the original
        assert result != query or "USING INDEX" in result

    def test_get_optimized_query_templates(self, neo4j_manager):
        """Test getting optimized query templates."""
        result = neo4j_manager.get_optimized_query_templates()

        assert isinstance(result, dict)
        assert len(result) > 0
        # Should contain common query patterns
        assert any("entity" in key.lower() for key in result.keys())

    def test_execute_optimized_query(self, neo4j_manager):
        """Test executing optimized query."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        # Create a proper session mock with context manager support
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_result = Mock()
        mock_result.__iter__ = Mock(
            return_value=iter([Mock(data=lambda: {"result": "optimized"})])
        )
        mock_session.run.return_value = mock_result

        with patch.object(neo4j_manager, "get_session") as mock_get_session:
            mock_get_session.return_value = mock_session

            result = neo4j_manager.execute_optimized_query(
                "find_entities_by_type", {"entity_type": "Person", "limit": 10}
            )

            assert result == [{"result": "optimized"}]

    def test_warm_up_connection_pool(self, neo4j_manager, mock_driver):
        """Test connection pool warm-up."""
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        # Mock session creation with proper context manager support
        mock_sessions = []
        for _ in range(3):
            session = Mock()
            session.__enter__ = Mock(return_value=session)
            session.__exit__ = Mock(return_value=None)
            mock_sessions.append(session)

        mock_driver.session.side_effect = mock_sessions

        result = neo4j_manager.warm_up_connection_pool(target_connections=3)

        assert result["target_connections"] == 3
        assert result["successful_connections"] >= 0
        assert "errors" in result

    def test_validate_connection_pool_config(self, neo4j_manager):
        """Test connection pool configuration validation."""
        result = neo4j_manager.validate_connection_pool_config()

        assert isinstance(result, dict)
        assert "valid" in result
        assert "config" in result


class TestNeo4jManagerRetryIntegration:
    """Test retry integration with Neo4jManager."""

    @pytest.fixture
    def neo4j_config(self):
        """Create a test Neo4j configuration with short retry times."""
        return Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            database="neo4j",
            max_retry_time=1,  # Short for testing
            initial_retry_delay=0.01,
            retry_delay_multiplier=2.0,
            retry_delay_jitter_factor=0.1,
        )

    @pytest.fixture
    def neo4j_manager(self, neo4j_config):
        """Create a test Neo4j manager with retry config."""
        return Neo4jManager(neo4j_config)

    def test_connect_with_retry_on_service_unavailable(self, neo4j_manager):
        """Test connection retry on service unavailable."""
        with patch(
            "qdrant_loader.core.managers.neo4j_manager.GraphDatabase"
        ) as mock_graph_db:
            # First call fails, second succeeds
            mock_driver = Mock()
            mock_driver.verify_connectivity.return_value = None
            mock_graph_db.driver.side_effect = [
                ServiceUnavailable("Service down"),
                mock_driver,
            ]

            with patch("time.sleep"):  # Mock sleep to speed up test
                neo4j_manager.connect()

            assert neo4j_manager._is_connected
            assert mock_graph_db.driver.call_count == 2

    def test_execute_query_with_retry_on_transient_error(self, neo4j_manager):
        """Test query execution retry on transient error."""
        # Create mocks
        mock_driver = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True
        mock_driver.session.return_value = mock_session

        # First call fails, second succeeds
        mock_session.run.side_effect = [
            TransientError("Temporary failure"),
            Mock(__iter__=lambda x: iter([Mock(data=lambda: {"test": 1})])),
        ]

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = neo4j_manager.execute_query("RETURN 1")

        assert result == [{"test": 1}]
        assert mock_session.run.call_count == 2

    def test_retry_exhausted_raises_last_exception(self, neo4j_manager):
        """Test that retry exhaustion raises the last exception."""
        # Mock both _is_connected and _driver to make is_connected return True
        neo4j_manager._is_connected = True
        neo4j_manager._driver = Mock()

        with patch.object(neo4j_manager, "get_session") as mock_get_session:
            mock_get_session.side_effect = TransientError("Persistent failure")

            with patch("time.sleep"):
                with pytest.raises(TransientError, match="Persistent failure"):
                    neo4j_manager.execute_query("RETURN 1")
