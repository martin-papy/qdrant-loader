"""Tests for Neo4j retry logic and connection pooling.

This module tests the retry decorator and connection pooling functionality
in the Neo4j manager.
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from neo4j.exceptions import (
    AuthError,
    ClientError,
    ConfigurationError,
    DatabaseError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)
from qdrant_loader.config.neo4j import Neo4jConfig
from qdrant_loader.core.managers.neo4j_manager import (
    Neo4jManager,
    _is_retryable_exception,
    retry_on_transient_failure,
)


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
        """Test that DatabaseError with retryable keywords is retryable (TransactionError has complex constructor)."""
        retryable_messages = [
            "deadlock detected",
            "lock timeout",
            "connection lost",
            "network error",
            "temporary failure",
        ]
        for message in retryable_messages:
            exception = DatabaseError(message)
            assert _is_retryable_exception(exception)

    def test_transaction_error_without_retryable_keywords(self):
        """Test that DatabaseError without retryable keywords is not retryable."""
        exception = DatabaseError("syntax error")
        assert _is_retryable_exception(exception) is False

    def test_database_error_with_retryable_keywords(self):
        """Test that DatabaseError with retryable keywords is retryable."""
        retryable_messages = [
            "timeout occurred",
            "connection failed",
            "network issue",
            "temporary unavailable",
        ]
        for message in retryable_messages:
            exception = DatabaseError(message)
            assert _is_retryable_exception(exception)

    def test_database_error_without_retryable_keywords(self):
        """Test that DatabaseError without retryable keywords is not retryable."""
        exception = DatabaseError("constraint violation")
        assert _is_retryable_exception(exception) is False

    def test_auth_error_is_not_retryable(self):
        """Test that AuthError is not retryable."""
        exception = AuthError("Invalid credentials")
        assert _is_retryable_exception(exception) is False

    def test_configuration_error_is_not_retryable(self):
        """Test that ConfigurationError is not retryable."""
        exception = ConfigurationError("Invalid config")
        assert _is_retryable_exception(exception) is False

    def test_client_error_is_not_retryable(self):
        """Test that ClientError is not retryable."""
        exception = ClientError("Client error")
        assert _is_retryable_exception(exception) is False

    def test_generic_exception_with_network_keywords(self):
        """Test that generic exceptions with network keywords are retryable."""
        retryable_messages = [
            "connection refused",
            "network timeout",
            "socket error",
            "broken pipe",
            "connection reset",
        ]
        for message in retryable_messages:
            exception = Exception(message)
            assert _is_retryable_exception(exception)

    def test_generic_exception_without_network_keywords(self):
        """Test that generic exceptions without network keywords are not retryable."""
        exception = Exception("some other error")
        assert _is_retryable_exception(exception) is False


class TestRetryDecorator:
    """Test the retry_on_transient_failure decorator."""

    def test_successful_operation_no_retry(self):
        """Test that successful operations don't trigger retries."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            max_retry_time=10,
            initial_retry_delay=1.0,
        )

        class MockManager:
            def __init__(self):
                self.config = config
                self.call_count = 0

            @retry_on_transient_failure()
            def test_method(self):
                self.call_count += 1
                return "success"

        manager = MockManager()
        result = manager.test_method()

        assert result == "success"
        assert manager.call_count == 1

    def test_non_retryable_exception_no_retry(self):
        """Test that non-retryable exceptions are not retried."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            max_retry_time=10,
            initial_retry_delay=1.0,
        )

        class MockManager:
            def __init__(self):
                self.config = config
                self.call_count = 0

            @retry_on_transient_failure()
            def test_method(self):
                self.call_count += 1
                raise AuthError("Invalid credentials")

        manager = MockManager()

        with pytest.raises(AuthError):
            manager.test_method()

        assert manager.call_count == 1

    def test_retryable_exception_with_eventual_success(self):
        """Test that retryable exceptions are retried until success."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            max_retry_time=10,
            initial_retry_delay=0.1,  # Short delay for testing
            retry_delay_multiplier=1.5,
        )

        class MockManager:
            def __init__(self):
                self.config = config
                self.call_count = 0

            @retry_on_transient_failure()
            def test_method(self):
                self.call_count += 1
                if self.call_count < 3:
                    raise ServiceUnavailable("Service temporarily down")
                return "success"

        manager = MockManager()

        with patch("time.sleep") as mock_sleep:
            result = manager.test_method()

        assert result == "success"
        assert manager.call_count == 3
        assert mock_sleep.call_count == 2  # Two retries

    def test_retryable_exception_all_retries_exhausted(self):
        """Test that retryable exceptions eventually give up after max retries."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            max_retry_time=1,  # Short time budget
            initial_retry_delay=0.1,
        )

        class MockManager:
            def __init__(self):
                self.config = config
                self.call_count = 0

            @retry_on_transient_failure()
            def test_method(self):
                self.call_count += 1
                raise ServiceUnavailable("Service permanently down")

        manager = MockManager()

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ServiceUnavailable):
                manager.test_method()

        assert manager.call_count > 1  # Should have retried
        assert mock_sleep.call_count > 0  # Should have slept between retries

    def test_exponential_backoff_with_jitter(self):
        """Test that retry delays follow exponential backoff with jitter."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            max_retry_time=10,
            initial_retry_delay=1.0,
            retry_delay_multiplier=2.0,
            retry_delay_jitter_factor=0.1,
        )

        class MockManager:
            def __init__(self):
                self.config = config
                self.call_count = 0

            @retry_on_transient_failure(max_retries=3)
            def test_method(self):
                self.call_count += 1
                raise ServiceUnavailable("Service down")

        manager = MockManager()
        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        with patch("time.sleep", side_effect=mock_sleep):
            with pytest.raises(ServiceUnavailable):
                manager.test_method()

        # Should have 3 sleep calls (for 3 retries)
        assert len(sleep_calls) == 3

        # Verify exponential backoff pattern (allowing for jitter)
        # The actual implementation uses: base_delay = initial_delay * (multiplier ** attempt)
        # where attempt starts from 0, so delays are: 1.0, 2.0, 4.0
        # But there's a max_delay cap of min(max_retry_time/4, 30.0) = min(10/4, 30) = 2.5
        # With jitter, the actual delay can vary by ±jitter_factor
        max_retry_delay = min(10 / 4, 30.0)  # 2.5 seconds
        for i, actual_delay in enumerate(sleep_calls):
            base_delay = 1.0 * (2.0**i)  # 1.0, 2.0, 4.0
            capped_delay = min(base_delay, max_retry_delay)  # Apply max delay cap
            jitter_range = capped_delay * 0.1  # 10% jitter
            min_delay = max(0.1, capped_delay - jitter_range)  # Minimum 0.1s
            max_delay = capped_delay + jitter_range
            assert (
                min_delay <= actual_delay <= max_delay
            ), "Delay {actual_delay} not in range [{min_delay}, {max_delay}] for attempt {i} (base_delay={base_delay}, capped_delay={capped_delay})"

    def test_time_budget_exceeded(self):
        """Test that retries stop when time budget is exceeded."""
        config = Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            max_retry_time=1,  # Short time budget (integer)
            initial_retry_delay=0.1,
        )

        class MockManager:
            def __init__(self):
                self.config = config
                self.call_count = 0

            @retry_on_transient_failure()
            def test_method(self):
                self.call_count += 1
                raise ServiceUnavailable("Service down")

        manager = MockManager()

        start_time = time.time()
        with patch("time.sleep"):  # Don't actually sleep
            with pytest.raises(ServiceUnavailable):
                manager.test_method()
        elapsed_time = time.time() - start_time

        # Should have stopped due to time budget, not max retries
        assert elapsed_time < 1.0  # Should finish quickly
        assert manager.call_count >= 2  # Should have tried at least twice


class TestNeo4jManagerRetryIntegration:
    """Test retry logic integration with Neo4jManager methods."""

    @pytest.fixture
    def neo4j_config(self):
        """Create a test Neo4j configuration."""
        return Neo4jConfig(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            max_retry_time=5,
            initial_retry_delay=0.1,
            retry_delay_multiplier=2.0,
        )

    @pytest.fixture
    def neo4j_manager(self, neo4j_config):
        """Create a Neo4j manager for testing."""
        return Neo4jManager(neo4j_config)

    def test_connect_with_retry_on_service_unavailable(self, neo4j_manager):
        """Test that connect() retries on ServiceUnavailable."""
        with patch(
            "qdrant_loader.core.managers.neo4j_manager.GraphDatabase"
        ) as mock_gdb:
            mock_driver = Mock()
            mock_gdb.driver.return_value = mock_driver

            # First call fails, second succeeds
            mock_driver.verify_connectivity.side_effect = [
                ServiceUnavailable("Service down"),
                None,  # Success
            ]

            with patch("time.sleep"):
                neo4j_manager.connect()

            # Should be called twice: first fails, second succeeds
            assert mock_driver.verify_connectivity.call_count == 2
            # Verify driver was created
            assert mock_gdb.driver.called
            assert neo4j_manager.is_connected

    def test_execute_query_with_retry_on_transient_error(self, neo4j_manager):
        """Test that execute_query() retries on transient errors."""
        # Mock the driver and session
        mock_driver = Mock()
        mock_session = Mock()
        mock_result = MagicMock()

        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        # Set up context manager for session
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_driver.session.return_value = mock_session_context

        # First call fails, second succeeds
        mock_session.run.side_effect = [
            TransientError("Temporary failure"),
            mock_result,
        ]
        # Make mock_result iterable and have data() method
        mock_record = Mock()
        mock_record.data.return_value = {"test": 1}
        mock_result.__iter__.return_value = iter([mock_record])

        with patch("time.sleep"):
            result = neo4j_manager.execute_query("RETURN 1 as test")

        assert result == [{"test": 1}]
        assert mock_session.run.call_count == 2

    def test_execute_write_transaction_with_retry(self, neo4j_manager):
        """Test that execute_write_transaction() retries on transient errors."""
        mock_driver = Mock()
        mock_session = Mock()

        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        # Set up context manager for session
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_driver.session.return_value = mock_session_context

        # First call fails, second succeeds
        mock_session.execute_write.side_effect = [
            SessionExpired("Session expired"),
            [{"created": 1}],
        ]

        with patch("time.sleep"):
            result = neo4j_manager.execute_write_transaction("CREATE (n:Test) RETURN n")

        assert result == [{"created": 1}]
        assert mock_session.execute_write.call_count == 2

    def test_test_connection_with_retry(self, neo4j_manager):
        """Test that test_connection() retries on failures."""
        # Mock the driver and ensure is_connected
        mock_driver = Mock()
        neo4j_manager._driver = mock_driver
        neo4j_manager._is_connected = True

        # Mock at the session level to test the retry logic properly
        mock_session = Mock()
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None

        with patch.object(
            neo4j_manager, "get_session", return_value=mock_session_context
        ):
            # First call fails, second succeeds
            mock_result = MagicMock()
            mock_record = Mock()
            mock_record.data.return_value = {"test": 1}
            mock_result.__iter__.return_value = iter([mock_record])

            mock_session.run.side_effect = [
                ServiceUnavailable("Service down"),
                mock_result,
            ]

            with patch("time.sleep"):
                result = neo4j_manager.test_connection()

            assert result
            assert mock_session.run.call_count == 2
