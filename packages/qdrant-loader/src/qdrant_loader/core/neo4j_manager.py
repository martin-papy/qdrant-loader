"""Neo4j database manager.

This module provides a manager class for Neo4j database operations,
including connection management and basic graph operations.
"""

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from neo4j import Driver, GraphDatabase, Session
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

from ..config import Neo4jConfig
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

# Type variable for retry decorator
T = TypeVar("T")


def retry_on_transient_failure(
    max_retries: int | None = None,
    initial_delay: float | None = None,
    max_delay: float | None = None,
    backoff_multiplier: float | None = None,
    jitter_factor: float | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry operations on transient failures with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts (uses config default if None)
        initial_delay: Initial delay between retries in seconds (uses config default if None)
        max_delay: Maximum delay between retries in seconds (uses config default if None)
        backoff_multiplier: Multiplier for exponential backoff (uses config default if None)
        jitter_factor: Jitter factor for randomizing delays (uses config default if None)

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            # Use instance config values as defaults
            config = getattr(self, "config", None)
            if config is None:
                raise RuntimeError(
                    "Retry decorator requires Neo4jManager instance with config"
                )

            # Calculate retry parameters from config
            max_retry_time = config.max_retry_time
            retry_initial_delay = initial_delay or config.initial_retry_delay
            retry_max_delay = max_delay or min(
                max_retry_time / 4, 30.0
            )  # Cap at 30s or 1/4 of max time
            retry_multiplier = backoff_multiplier or config.retry_delay_multiplier
            retry_jitter = jitter_factor or config.retry_delay_jitter_factor

            # Calculate max retries based on time budget if not specified
            if max_retries is None:
                # Estimate max retries based on time budget and delay progression
                estimated_retries = 0
                total_time = 0
                delay = retry_initial_delay
                while (
                    total_time < max_retry_time and estimated_retries < 10
                ):  # Cap at 10 retries
                    total_time += delay
                    delay = min(delay * retry_multiplier, retry_max_delay)
                    estimated_retries += 1
                retry_attempts = max(1, estimated_retries)
            else:
                retry_attempts = max_retries

            last_exception: Exception | None = None
            start_time = time.time()

            for attempt in range(retry_attempts + 1):  # +1 for initial attempt
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    if not _is_retryable_exception(e):
                        logger.debug(
                            "Non-retryable exception in {func.__name__}",
                            extra={"error": str(e), "exception_type": type(e).__name__},
                        )
                        raise

                    # Check if we've exceeded time budget
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= max_retry_time:
                        logger.warning(
                            "Retry time budget exceeded for {func.__name__}",
                            extra={
                                "elapsed_time": elapsed_time,
                                "max_retry_time": max_retry_time,
                                "attempts": attempt + 1,
                            },
                        )
                        break

                    # Don't sleep after the last attempt
                    if attempt < retry_attempts:
                        # Calculate delay with exponential backoff and jitter
                        base_delay = retry_initial_delay * (retry_multiplier**attempt)
                        capped_delay = min(base_delay, retry_max_delay)

                        # Add jitter to prevent thundering herd
                        jitter = (
                            random.uniform(-retry_jitter, retry_jitter) * capped_delay
                        )
                        actual_delay = max(
                            0.1, capped_delay + jitter
                        )  # Minimum 100ms delay

                        logger.warning(
                            "Transient failure in {func.__name__}, retrying",
                            extra={
                                "error": str(e),
                                "exception_type": type(e).__name__,
                                "attempt": attempt + 1,
                                "max_attempts": retry_attempts + 1,
                                "delay": actual_delay,
                                "elapsed_time": elapsed_time,
                            },
                        )

                        time.sleep(actual_delay)

            # All retries exhausted - last_exception should never be None here
            if last_exception is None:
                raise RuntimeError(
                    "Unexpected error: no exception recorded in {func.__name__}"
                )

            logger.error(
                "All retry attempts exhausted for {func.__name__}",
                extra={
                    "final_error": str(last_exception),
                    "exception_type": type(last_exception).__name__,
                    "total_attempts": retry_attempts + 1,
                    "total_time": time.time() - start_time,
                },
            )
            raise last_exception

        return wrapper

    return decorator


def _is_retryable_exception(exception: Exception) -> bool:
    """Determine if an exception is retryable.

    Args:
        exception: The exception to check

    Returns:
        True if the exception is retryable, False otherwise
    """
    # Neo4j transient errors are always retryable
    if isinstance(exception, TransientError):
        return True

    # Service unavailable is retryable
    if isinstance(exception, ServiceUnavailable):
        return True

    # Session expired is retryable
    if isinstance(exception, SessionExpired):
        return True

    # Some transaction errors are retryable
    if isinstance(exception, TransactionError):
        error_msg = str(exception).lower()
        retryable_transaction_errors = [
            "deadlock",
            "lock",
            "timeout",
            "connection",
            "network",
            "temporary",
        ]
        return any(keyword in error_msg for keyword in retryable_transaction_errors)

    # Some database errors are retryable
    if isinstance(exception, DatabaseError):
        error_msg = str(exception).lower()
        retryable_db_errors = [
            "deadlock",
            "lock",
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable",
        ]
        return any(keyword in error_msg for keyword in retryable_db_errors)

    # Authentication and configuration errors are not retryable
    if isinstance(exception, (AuthError, ConfigurationError, ClientError)):
        return False

    # For generic exceptions, check the error message for network-related issues
    error_msg = str(exception).lower()
    retryable_keywords = [
        "connection",
        "network",
        "timeout",
        "temporary",
        "unavailable",
        "refused",
        "reset",
        "broken pipe",
        "socket",
    ]

    return any(keyword in error_msg for keyword in retryable_keywords)


class Neo4jManager:
    """Manager for Neo4j database operations."""

    def __init__(self, config: Neo4jConfig):
        """Initialize the Neo4j manager.

        Args:
            config: Neo4j configuration settings
        """
        self.config = config
        self._driver: Driver | None = None
        self._is_connected = False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    @retry_on_transient_failure()
    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        if self._driver is not None:
            logger.debug("Neo4j driver already initialized")
            return

        try:
            logger.info("Connecting to Neo4j database", extra={"uri": self.config.uri})

            # Get driver configuration from config
            driver_config = self.config.get_driver_config()

            # Handle trusted_certificates parameter (replaces deprecated trust)
            trusted_certs = driver_config.get("trusted_certificates")
            if trusted_certs and isinstance(trusted_certs, str):
                # Convert string values to proper Neo4j objects
                if trusted_certs == "TRUST_ALL_CERTIFICATES":
                    try:
                        from neo4j import TrustAll

                        driver_config["trusted_certificates"] = TrustAll()
                    except ImportError:
                        # Fallback for older driver versions
                        driver_config["trust"] = trusted_certs
                elif trusted_certs == "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES":
                    try:
                        from neo4j import TrustSystemCAs

                        driver_config["trusted_certificates"] = TrustSystemCAs()
                    except ImportError:
                        # Fallback for older driver versions
                        driver_config["trust"] = trusted_certs

            # Create driver with configuration
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password),
                **driver_config,  # type: ignore
            )

            # Test the connection
            self._driver.verify_connectivity()
            self._is_connected = True

            logger.info("Successfully connected to Neo4j database")

        except AuthError as e:
            logger.error("Neo4j authentication failed", extra={"error": str(e)})
            # Clean up driver on auth failure
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            raise
        except ConfigurationError as e:
            logger.error("Neo4j configuration error", extra={"error": str(e)})
            # Clean up driver on config failure
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            raise
        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailable", extra={"error": str(e)})
            # Clean up driver on service unavailable (for retry)
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            raise
        except Exception as e:
            logger.error(
                "Unexpected error connecting to Neo4j", extra={"error": str(e)}
            )
            # Clean up driver on any other failure
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            raise

    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver is not None:
            logger.info("Closing Neo4j connection")
            self._driver.close()
            self._driver = None
            self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        return self._is_connected and self._driver is not None

    def get_session(
        self, database: str | None = None, access_mode: str | None = None
    ) -> Session:
        """Get a Neo4j session.

        Args:
            database: Optional database name, defaults to configured database
            access_mode: Optional access mode ('READ' or 'WRITE'), defaults to config preference

        Returns:
            Neo4j session

        Raises:
            RuntimeError: If not connected to Neo4j
        """
        if not self.is_connected or self._driver is None:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        db_name = database or self.config.database

        # Basic session configuration
        session_config = {"database": db_name}

        # Add Enterprise routing if configured
        if access_mode:
            try:
                from neo4j import READ_ACCESS, WRITE_ACCESS

                if access_mode.upper() == "READ":
                    session_config["default_access_mode"] = READ_ACCESS
                elif access_mode.upper() == "WRITE":
                    session_config["default_access_mode"] = WRITE_ACCESS
            except ImportError:
                # Older Neo4j driver versions
                pass
        elif self.config.routing and self.config.read_preference == "read":
            try:
                from neo4j import READ_ACCESS

                session_config["default_access_mode"] = READ_ACCESS
            except ImportError:
                pass

        return self._driver.session(**session_config)  # type: ignore

    @retry_on_transient_failure()
    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        access_mode: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name
            access_mode: Optional access mode ('READ' or 'WRITE') for Enterprise routing

        Returns:
            List of result records as dictionaries

        Raises:
            RuntimeError: If not connected to Neo4j
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        logger.debug(
            "Executing Neo4j query",
            extra={"query": query[:100] + "..." if len(query) > 100 else query},
        )

        try:
            with self.get_session(database, access_mode) as session:
                # Cast query to satisfy type checker
                result = session.run(cast(str, query), parameters or {})  # type: ignore
                records = [record.data() for record in result]
                logger.debug(
                    "Query executed successfully", extra={"record_count": len(records)}
                )
                return records

        except Exception as e:
            logger.error(
                "Error executing Neo4j query",
                extra={"error": str(e), "query": query[:100]},
            )
            raise

    @retry_on_transient_failure()
    def execute_write_transaction(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            List of result records as dictionaries
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        def _write_tx(tx):
            result = tx.run(cast(str, query), parameters or {})
            return [record.data() for record in result]

        try:
            with self.get_session(database) as session:
                records = session.execute_write(_write_tx)
                logger.debug(
                    "Write transaction executed successfully",
                    extra={"record_count": len(records)},
                )
                return records

        except Exception as e:
            logger.error(
                "Error executing Neo4j write transaction", extra={"error": str(e)}
            )
            raise

    @retry_on_transient_failure()
    def execute_read_transaction(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            List of result records as dictionaries
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        def _read_tx(tx):
            result = tx.run(cast(str, query), parameters or {})
            return [record.data() for record in result]

        try:
            with self.get_session(database) as session:
                records = session.execute_read(_read_tx)
                logger.debug(
                    "Read transaction executed successfully",
                    extra={"record_count": len(records)},
                )
                return records

        except Exception as e:
            logger.error(
                "Error executing Neo4j read transaction", extra={"error": str(e)}
            )
            raise

    @retry_on_transient_failure()
    def test_connection(self) -> bool:
        """Test the Neo4j connection.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            if not self.is_connected:
                self.connect()

            # Simple test query
            result = self.execute_query("RETURN 1 as test")
            return len(result) == 1 and result[0].get("test") == 1

        except Exception as e:
            logger.error("Neo4j connection test failed", extra={"error": str(e)})
            return False

    def get_database_info(self) -> dict[str, Any]:
        """Get information about the Neo4j database.

        Returns:
            Dictionary containing database information
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        try:
            info = {
                "database": self.config.database,
                "uri": self.config.uri,
                "edition": "unknown",
                "version": "unknown",
                "apoc_procedures": 0,
                "statistics": {},
                "available_databases": [],
            }

            # Try to get version and edition info
            try:
                # This works in both Community and Enterprise
                version_result = self.execute_query(
                    "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition",
                    database="system",
                )
                if version_result:
                    info["version_info"] = version_result
                    # Extract edition if available
                    for component in version_result:
                        if component.get("name") == "Neo4j Kernel":
                            info["edition"] = component.get("edition", "unknown")
                            if component.get("versions"):
                                info["version"] = (
                                    component["versions"][0]
                                    if component["versions"]
                                    else "unknown"
                                )
            except Exception as e:
                logger.debug(
                    "Could not get version info from system database",
                    extra={"error": str(e)},
                )
                # Fallback: try without system database (older versions)
                try:
                    version_result = self.execute_query(
                        "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition"
                    )
                    info["version_info"] = version_result
                except Exception:
                    logger.debug("Version info not available")

            # Get database statistics
            try:
                stats_result = self.execute_query(
                    """
                    MATCH (n)
                    RETURN
                        count(n) as node_count,
                        count{(n)-[]->()} as relationship_count
                    LIMIT 1
                """
                )
                info["statistics"] = stats_result[0] if stats_result else {}
            except Exception as e:
                logger.debug(
                    "Could not get database statistics", extra={"error": str(e)}
                )

            # Check APOC availability
            try:
                apoc_result = self.execute_query(
                    "RETURN apoc.version() as apoc_version"
                )
                if apoc_result and apoc_result[0].get("apoc_version"):
                    info["apoc_version"] = apoc_result[0]["apoc_version"]

                    # Count APOC procedures if available
                    try:
                        procedures_result = self.execute_query(
                            """
                            CALL dbms.procedures()
                            YIELD name
                            WHERE name STARTS WITH 'apoc'
                            RETURN count(name) as apoc_procedures
                        """,
                            database="system",
                        )
                        info["apoc_procedures"] = (
                            procedures_result[0].get("apoc_procedures", 0)
                            if procedures_result
                            else 0
                        )
                    except Exception:
                        # Fallback for older versions or Community edition
                        info["apoc_procedures"] = "available"
            except Exception as e:
                logger.debug("APOC not available", extra={"error": str(e)})

            # Enterprise feature: List available databases
            try:
                # This only works in Enterprise edition
                db_result = self.execute_query("SHOW DATABASES", database="system")
                info["available_databases"] = [
                    db["name"] for db in db_result if db.get("name")
                ]
                info["enterprise_features"] = True
            except Exception as e:
                logger.debug(
                    "Enterprise database listing not available", extra={"error": str(e)}
                )
                info["enterprise_features"] = False
                info["available_databases"] = [
                    self.config.database
                ]  # Only the configured database

            # Enterprise feature: Check clustering status
            try:
                cluster_result = self.execute_query(
                    "CALL dbms.cluster.overview()", database="system"
                )
                info["cluster_info"] = cluster_result
                info["clustered"] = True
            except Exception as e:
                logger.debug(
                    "Cluster information not available", extra={"error": str(e)}
                )
                info["clustered"] = False

            return info

        except Exception as e:
            logger.error("Error getting Neo4j database info", extra={"error": str(e)})
            raise

    def create_indexes(self) -> None:
        """Create common indexes for better performance."""
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        indexes = [
            # Common document indexes
            "CREATE INDEX document_id_index IF NOT EXISTS FOR (d:Document) ON (d.id)",
            "CREATE INDEX document_source_index IF NOT EXISTS FOR (d:Document) ON (d.source)",
            "CREATE INDEX document_type_index IF NOT EXISTS FOR (d:Document) ON (d.type)",
            # Common chunk indexes
            "CREATE INDEX chunk_id_index IF NOT EXISTS FOR (c:Chunk) ON (c.id)",
            "CREATE INDEX chunk_document_index IF NOT EXISTS FOR (c:Chunk) ON (c.document_id)",
            # Full-text search indexes
            "CREATE FULLTEXT INDEX document_content_fulltext IF NOT EXISTS FOR (d:Document) ON EACH [d.title, d.content]",
            "CREATE FULLTEXT INDEX chunk_content_fulltext IF NOT EXISTS FOR (c:Chunk) ON EACH [c.content]",
        ]

        for index_query in indexes:
            try:
                self.execute_write_transaction(index_query)
                logger.debug("Created index", extra={"query": index_query})
            except Exception as e:
                # Index might already exist, log but don't fail
                logger.debug(
                    "Index creation skipped (may already exist)",
                    extra={"error": str(e), "query": index_query},
                )

    def clear_database(self) -> None:
        """Clear all data from the database. Use with caution!"""
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        logger.warning("Clearing all data from Neo4j database")

        try:
            # Delete all relationships first, then nodes
            self.execute_write_transaction("MATCH ()-[r]-() DELETE r")
            self.execute_write_transaction("MATCH (n) DELETE n")
            logger.info("Successfully cleared Neo4j database")

        except Exception as e:
            logger.error("Error clearing Neo4j database", extra={"error": str(e)})
            raise

    def execute_read_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read-only query (Enterprise: routes to read replicas).

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            List of result records as dictionaries
        """
        return self.execute_query(query, parameters, database, access_mode="READ")

    def execute_write_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a write query (Enterprise: routes to write instances).

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            List of result records as dictionaries
        """
        return self.execute_query(query, parameters, database, access_mode="WRITE")
