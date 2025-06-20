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

from ...config import Neo4jConfig
from ...utils.logging import LoggingConfig

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
                            f"Non-retryable exception in {func.__name__}",
                            extra={"error": str(e), "exception_type": type(e).__name__},
                        )
                        raise

                    # Check if we've exceeded time budget
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= max_retry_time:
                        logger.warning(
                            f"Retry time budget exceeded for {func.__name__}",
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
                            f"Transient failure in {func.__name__}, retrying",
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
                    f"Unexpected error: no exception recorded in {func.__name__}"
                )

            logger.error(
                f"All retry attempts exhausted for {func.__name__}",
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
        # Check both str() and args for the error message
        error_msg = str(exception).lower()
        if not error_msg and exception.args:
            error_msg = str(exception.args[0]).lower()
        # Also check the message attribute if available
        if not error_msg and hasattr(exception, "message") and exception.message:
            error_msg = str(exception.message).lower()

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
            logger.info("Connecting to Neo4j databasef", extra={"uri": self.config.uri})

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
            logger.error("Neo4j authentication failedf", extra={"error": str(e)})
            # Clean up driver on auth failure
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            raise
        except ConfigurationError as e:
            logger.error("Neo4j configuration errorf", extra={"error": str(e)})
            # Clean up driver on config failure
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            raise
        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailablef", extra={"error": str(e)})
            # Clean up driver on service unavailable (for retry)
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            raise
        except Exception as e:
            logger.error(
                "Unexpected error connecting to Neo4jf", extra={"error": str(e)}
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
            raise RuntimeError("Not connected to Neo4j. Call connect() first.f")

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
            "Executing Neo4j queryf",
            extra={"query": query[:100] + "..." if len(query) > 100 else query},
        )

        try:
            with self.get_session(database, access_mode) as session:
                # Cast query to satisfy type checker
                result = session.run(cast(str, query), parameters or {})  # type: ignore
                records = [record.data() for record in result]
                logger.debug(
                    "Query executed successfullyf", extra={"record_count": len(records)}
                )
                return records

        except Exception as e:
            logger.error(
                "Error executing Neo4j queryf",
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
                    "Write transaction executed successfullyf",
                    extra={"record_count": len(records)},
                )
                return records

        except Exception as e:
            logger.error(
                "Error executing Neo4j write transactionf", extra={"error": str(e)}
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
                    "Read transaction executed successfullyf",
                    extra={"record_count": len(records)},
                )
                return records

        except Exception as e:
            logger.error(
                "Error executing Neo4j read transactionf", extra={"error": str(e)}
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
            logger.error("Neo4j connection test failedf", extra={"error": str(e)})
            return False

    def get_database_info(self) -> dict[str, Any]:
        """Get information about the Neo4j database.

        Returns:
            Dictionary containing database information
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.f")

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
                    "Could not get version info from system databasef",
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
                    "Could not get database statisticsf", extra={"error": str(e)}
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
                logger.debug("APOC not availablef", extra={"error": str(e)})

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
                    "Enterprise database listing not availablef",
                    extra={"error": str(e)},
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
                    "Cluster information not availablef", extra={"error": str(e)}
                )
                info["clustered"] = False

            return info

        except Exception as e:
            logger.error("Error getting Neo4j database infof", extra={"error": str(e)})
            raise

    def create_indexes(self) -> None:
        """Create comprehensive indexes for better performance in graph operations."""
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        # Basic property indexes for common node types
        property_indexes = [
            # Document indexes
            "CREATE INDEX document_id_index IF NOT EXISTS FOR (d:Document) ON (d.id)",
            "CREATE INDEX document_source_index IF NOT EXISTS FOR (d:Document) ON (d.source)",
            "CREATE INDEX document_type_index IF NOT EXISTS FOR (d:Document) ON (d.type)",
            "CREATE INDEX document_created_at_index IF NOT EXISTS FOR (d:Document) ON (d.created_at)",
            # Chunk indexes
            "CREATE INDEX chunk_id_index IF NOT EXISTS FOR (c:Chunk) ON (c.id)",
            "CREATE INDEX chunk_document_index IF NOT EXISTS FOR (c:Chunk) ON (c.document_id)",
            "CREATE INDEX chunk_created_at_index IF NOT EXISTS FOR (c:Chunk) ON (c.created_at)",
            # Entity indexes (for Graphiti nodes)
            "CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_uuid_index IF NOT EXISTS FOR (e:Entity) ON (e.uuid)",
            "CREATE INDEX entity_created_at_index IF NOT EXISTS FOR (e:Entity) ON (e.created_at)",
            # Person indexes
            "CREATE INDEX person_name_index IF NOT EXISTS FOR (p:Person) ON (p.name)",
            "CREATE INDEX person_uuid_index IF NOT EXISTS FOR (p:Person) ON (p.uuid)",
            # Organization indexes
            "CREATE INDEX organization_name_index IF NOT EXISTS FOR (o:Organization) ON (o.name)",
            "CREATE INDEX organization_uuid_index IF NOT EXISTS FOR (o:Organization) ON (o.uuid)",
            # Concept indexes
            "CREATE INDEX concept_name_index IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX concept_uuid_index IF NOT EXISTS FOR (c:Concept) ON (c.uuid)",
            # Event indexes
            "CREATE INDEX event_name_index IF NOT EXISTS FOR (e:Event) ON (e.name)",
            "CREATE INDEX event_uuid_index IF NOT EXISTS FOR (e:Event) ON (e.uuid)",
            "CREATE INDEX event_timestamp_index IF NOT EXISTS FOR (e:Event) ON (e.timestamp)",
            # Location indexes
            "CREATE INDEX location_name_index IF NOT EXISTS FOR (l:Location) ON (l.name)",
            "CREATE INDEX location_uuid_index IF NOT EXISTS FOR (l:Location) ON (l.uuid)",
            # Episode indexes (Graphiti episodes)
            "CREATE INDEX episode_uuid_index IF NOT EXISTS FOR (ep:Episode) ON (ep.uuid)",
            "CREATE INDEX episode_name_index IF NOT EXISTS FOR (ep:Episode) ON (ep.name)",
            "CREATE INDEX episode_created_at_index IF NOT EXISTS FOR (ep:Episode) ON (ep.created_at)",
            "CREATE INDEX episode_reference_time_index IF NOT EXISTS FOR (ep:Episode) ON (ep.reference_time)",
        ]

        # Composite indexes for common query patterns
        composite_indexes = [
            # Entity type and name combination for efficient filtering
            "CREATE INDEX entity_type_name_index IF NOT EXISTS FOR (e:Entity) ON (e.type, e.name)",
            # Document source and type combination
            "CREATE INDEX document_source_type_index IF NOT EXISTS FOR (d:Document) ON (d.source, d.type)",
            # Temporal queries - created_at with type
            "CREATE INDEX entity_type_created_index IF NOT EXISTS FOR (e:Entity) ON (e.type, e.created_at)",
            "CREATE INDEX document_type_created_index IF NOT EXISTS FOR (d:Document) ON (d.type, d.created_at)",
        ]

        # Full-text search indexes for content search
        fulltext_indexes = [
            "CREATE FULLTEXT INDEX document_content_fulltext IF NOT EXISTS FOR (d:Document) ON EACH [d.title, d.content]",
            "CREATE FULLTEXT INDEX chunk_content_fulltext IF NOT EXISTS FOR (c:Chunk) ON EACH [c.content]",
            "CREATE FULLTEXT INDEX entity_text_fulltext IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.summary]",
            "CREATE FULLTEXT INDEX episode_content_fulltext IF NOT EXISTS FOR (ep:Episode) ON EACH [ep.name, ep.content]",
        ]

        # Constraints for data integrity
        constraints = [
            # Unique constraints for UUIDs
            "CREATE CONSTRAINT entity_uuid_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.uuid IS UNIQUE",
            "CREATE CONSTRAINT episode_uuid_unique IF NOT EXISTS FOR (ep:Episode) REQUIRE ep.uuid IS UNIQUE",
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
            # Node key constraints for common lookup patterns
            "CREATE CONSTRAINT entity_name_type_key IF NOT EXISTS FOR (e:Entity) REQUIRE (e.name, e.type) IS NODE KEY",
        ]

        # Execute all index creation queries
        all_indexes = (
            property_indexes + composite_indexes + fulltext_indexes + constraints
        )

        created_count = 0
        skipped_count = 0

        for index_query in all_indexes:
            try:
                self.execute_write_transaction(index_query)
                logger.debug("Created index/constraint", extra={"query": index_query})
                created_count += 1
            except Exception as e:
                # Index/constraint might already exist, log but don't fail
                logger.debug(
                    "Index/constraint creation skipped (may already exist)",
                    extra={"error": str(e), "query": index_query},
                )
                skipped_count += 1

        logger.info(
            "Index creation completed",
            extra={
                "created": created_count,
                "skipped": skipped_count,
                "total": len(all_indexes),
            },
        )

    def analyze_query_performance(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Analyze query performance and provide optimization suggestions.

        Args:
            query: Cypher query to analyze
            parameters: Query parameters

        Returns:
            Dictionary containing performance analysis results
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        analysis_results = {}

        try:
            # Get query execution plan
            explain_query = f"EXPLAIN {query}"
            explain_result = self.execute_query(explain_query, parameters)
            analysis_results["execution_plan"] = explain_result

            # Get query profile (actual execution statistics)
            profile_query = f"PROFILE {query}"
            profile_result = self.execute_query(profile_query, parameters)
            analysis_results["profile"] = profile_result

            # Extract key performance metrics from profile
            if profile_result:
                # This is a simplified extraction - actual implementation would parse the plan tree
                analysis_results["performance_summary"] = {
                    "total_db_hits": "See profile for details",
                    "rows_returned": len(profile_result),
                    "optimization_suggestions": self._generate_optimization_suggestions(
                        query
                    ),
                }

            logger.debug(
                "Query performance analysis completed", extra={"query": query[:100]}
            )

        except Exception as e:
            logger.error(
                "Failed to analyze query performance",
                extra={"error": str(e), "query": query[:100]},
            )
            analysis_results["error"] = str(e)

        return analysis_results

    def _generate_optimization_suggestions(self, query: str) -> list[str]:
        """Generate optimization suggestions based on query patterns.

        Args:
            query: Cypher query to analyze

        Returns:
            List of optimization suggestions
        """
        suggestions = []
        query_lower = query.lower()

        # Check for common anti-patterns
        if "match (n)" in query_lower and "where" not in query_lower:
            suggestions.append("Consider adding WHERE clause to filter nodes early")

        if "match" in query_lower and "limit" not in query_lower:
            suggestions.append("Consider adding LIMIT clause for large result sets")

        if "order by" in query_lower and "limit" not in query_lower:
            suggestions.append(
                "ORDER BY without LIMIT can be expensive on large datasets"
            )

        if query_lower.count("match") > 3:
            suggestions.append(
                "Multiple MATCH clauses - consider using WITH to pipeline results"
            )

        if "collect(" in query_lower:
            suggestions.append(
                "COLLECT operations can be memory intensive - consider pagination"
            )

        # Check for missing index opportunities
        if "n.name" in query_lower or "e.name" in query_lower:
            suggestions.append(
                "Ensure name properties are indexed for better performance"
            )

        if "created_at" in query_lower:
            suggestions.append(
                "Ensure temporal properties are indexed for time-based queries"
            )

        if "uuid" in query_lower:
            suggestions.append(
                "UUID lookups should use unique constraints for optimal performance"
            )

        return suggestions

    def get_index_usage_stats(self) -> dict[str, Any]:
        """Get statistics about index usage and effectiveness.

        Returns:
            Dictionary containing index usage statistics
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        stats = {}

        try:
            # Get list of all indexes
            indexes_result = self.execute_query("SHOW INDEXES")
            stats["total_indexes"] = len(indexes_result)
            stats["indexes"] = indexes_result

            # Get list of all constraints
            constraints_result = self.execute_query("SHOW CONSTRAINTS")
            stats["total_constraints"] = len(constraints_result)
            stats["constraints"] = constraints_result

            # Get database statistics
            db_stats = self.execute_query(
                """
                MATCH (n)
                RETURN 
                    count(n) as total_nodes,
                    count{(n)-[]->()} as total_relationships,
                    [label IN labels(n) | label] as all_labels
                LIMIT 1
            """
            )

            if db_stats:
                stats["database_stats"] = db_stats[0]

            logger.debug("Index usage statistics retrieved")

        except Exception as e:
            logger.error(
                "Failed to get index usage statistics", extra={"error": str(e)}
            )
            stats["error"] = str(e)

        return stats

    def get_connection_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics and health information.

        Returns:
            Dictionary containing connection pool statistics
        """
        if not self.is_connected or self._driver is None:
            return {"error": "Not connected to Neo4j"}

        stats = {}

        try:
            # Get basic driver information
            stats["driver_info"] = {
                "encrypted": getattr(self._driver, "encrypted", "unknown"),
                "trust": getattr(self._driver, "trust", "unknown"),
                "user_agent": getattr(self._driver, "user_agent", "unknown"),
            }

            # Get connection pool configuration
            stats["pool_config"] = {
                "max_connection_pool_size": self.config.max_connection_pool_size,
                "max_connection_lifetime": self.config.max_connection_lifetime,
                "connection_acquisition_timeout": self.config.connection_acquisition_timeout,
                "max_retry_time": self.config.max_retry_time,
            }

            # Test connection health
            health_start = time.time()
            is_healthy = self.test_connection()
            health_duration = time.time() - health_start

            stats["health"] = {
                "is_healthy": is_healthy,
                "health_check_duration_ms": round(health_duration * 1000, 2),
                "last_health_check": time.time(),
            }

            # Get database info for additional context
            try:
                db_info = self.get_database_info()
                stats["database_info"] = {
                    "version": db_info.get("version", "unknown"),
                    "edition": db_info.get("edition", "unknown"),
                    "clustered": db_info.get("clustered", False),
                    "enterprise_features": db_info.get("enterprise_features", False),
                }
            except Exception as e:
                stats["database_info"] = {"error": str(e)}

            logger.debug("Connection pool statistics retrieved")

        except Exception as e:
            logger.error(
                "Failed to get connection pool statistics", extra={"error": str(e)}
            )
            stats["error"] = str(e)

        return stats

    def validate_connection_pool_config(self) -> dict[str, Any]:
        """Validate and provide recommendations for connection pool configuration.

        Returns:
            Dictionary containing validation results and recommendations
        """
        validation = {
            "valid": True,
            "warnings": [],
            "recommendations": [],
            "config": self.config.to_dict(),
        }

        # Check pool size
        if self.config.max_connection_pool_size < 10:
            validation["warnings"].append(
                f"Connection pool size ({self.config.max_connection_pool_size}) is quite small. "
                "Consider increasing for better concurrency."
            )
        elif self.config.max_connection_pool_size > 200:
            validation["warnings"].append(
                f"Connection pool size ({self.config.max_connection_pool_size}) is very large. "
                "This may consume excessive resources."
            )

        # Check connection lifetime
        if self.config.max_connection_lifetime < 300:  # 5 minutes
            validation["warnings"].append(
                f"Connection lifetime ({self.config.max_connection_lifetime}s) is very short. "
                "This may cause frequent reconnections."
            )
        elif self.config.max_connection_lifetime > 7200:  # 2 hours
            validation["recommendations"].append(
                f"Connection lifetime ({self.config.max_connection_lifetime}s) is quite long. "
                "Consider shorter lifetime for better connection freshness."
            )

        # Check acquisition timeout
        if self.config.connection_acquisition_timeout < 10:
            validation["warnings"].append(
                f"Connection acquisition timeout ({self.config.connection_acquisition_timeout}s) is very short. "
                "This may cause premature timeouts under load."
            )
        elif self.config.connection_acquisition_timeout > 120:
            validation["recommendations"].append(
                f"Connection acquisition timeout ({self.config.connection_acquisition_timeout}s) is quite long. "
                "Consider shorter timeout for faster failure detection."
            )

        # Check retry settings
        if self.config.max_retry_time < 5:
            validation["warnings"].append(
                f"Max retry time ({self.config.max_retry_time}s) is very short. "
                "This may not allow sufficient time for transient error recovery."
            )

        # Provide general recommendations
        validation["recommendations"].extend(
            [
                "Monitor connection pool usage under typical load",
                "Adjust pool size based on concurrent user count and query patterns",
                "Consider read/write separation for Enterprise deployments",
                "Use connection pool monitoring in production environments",
            ]
        )

        return validation

    def warm_up_connection_pool(
        self, target_connections: int | None = None
    ) -> dict[str, Any]:
        """Warm up the connection pool by creating initial connections.

        Args:
            target_connections: Number of connections to create (defaults to 25% of pool size)

        Returns:
            Dictionary containing warm-up results
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        if target_connections is None:
            target_connections = max(1, self.config.max_connection_pool_size // 4)

        results = {
            "target_connections": target_connections,
            "successful_connections": 0,
            "failed_connections": 0,
            "total_time_ms": 0,
            "errors": [],
        }

        start_time = time.time()

        # Create multiple concurrent sessions to warm up the pool
        import concurrent.futures

        def create_test_session():
            try:
                with self.get_session() as session:
                    # Simple query to establish connection
                    session.run("RETURN 1 as test").single()
                return True
            except Exception as e:
                return str(e)

        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(target_connections, 10)
            ) as executor:
                futures = [
                    executor.submit(create_test_session)
                    for _ in range(target_connections)
                ]

                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result is True:
                        results["successful_connections"] += 1
                    else:
                        results["failed_connections"] += 1
                        results["errors"].append(str(result))

        except Exception as e:
            results["errors"].append(f"Pool warm-up failed: {str(e)}")

        results["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "Connection pool warm-up completed",
            extra={
                "successful": results["successful_connections"],
                "failed": results["failed_connections"],
                "duration_ms": results["total_time_ms"],
            },
        )

        return results

    def get_optimized_query_templates(self) -> dict[str, str]:
        """Get a collection of optimized query templates for common graph operations.

        Returns:
            Dictionary of query templates optimized for performance
        """
        return {
            # Entity lookup queries
            "find_entity_by_uuid": """
                MATCH (e:Entity {uuid: $uuid})
                RETURN e
            """,
            "find_entities_by_type": """
                MATCH (e:Entity)
                WHERE e.type = $entity_type
                RETURN e
                ORDER BY e.created_at DESC
                LIMIT $limit
            """,
            "find_entities_by_name_pattern": """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $name_pattern
                RETURN e
                ORDER BY e.name
                LIMIT $limit
            """,
            # Relationship traversal queries
            "find_related_entities": """
                MATCH (e:Entity {uuid: $uuid})-[r]-(related:Entity)
                RETURN related, type(r) as relationship_type, r
                ORDER BY related.name
                LIMIT $limit
            """,
            "find_entities_in_episode": """
                MATCH (ep:Episode {uuid: $episode_uuid})-[:CONTAINS]->(e:Entity)
                RETURN e
                ORDER BY e.created_at
                LIMIT $limit
            """,
            # Document and chunk queries
            "find_chunks_by_document": """
                MATCH (d:Document {id: $document_id})-[:CONTAINS]->(c:Chunk)
                RETURN c
                ORDER BY c.chunk_index
            """,
            "find_entities_in_document": """
                MATCH (d:Document {id: $document_id})-[:CONTAINS]->(c:Chunk)-[:MENTIONS]->(e:Entity)
                RETURN DISTINCT e, count(c) as mention_count
                ORDER BY mention_count DESC
                LIMIT $limit
            """,
            # Temporal queries
            "find_recent_entities": """
                MATCH (e:Entity)
                WHERE e.created_at >= $since_timestamp
                RETURN e
                ORDER BY e.created_at DESC
                LIMIT $limit
            """,
            "find_entities_in_timeframe": """
                MATCH (e:Entity)
                WHERE e.created_at >= $start_time AND e.created_at <= $end_time
                RETURN e
                ORDER BY e.created_at
                LIMIT $limit
            """,
            # Graph traversal queries
            "find_shortest_path": """
                MATCH path = shortestPath((start:Entity {uuid: $start_uuid})-[*..5]-(end:Entity {uuid: $end_uuid}))
                RETURN path
            """,
            "find_connected_component": """
                MATCH (start:Entity {uuid: $start_uuid})-[*..3]-(connected:Entity)
                RETURN DISTINCT connected
                ORDER BY connected.name
                LIMIT $limit
            """,
            # Aggregation queries
            "count_entities_by_type": """
                MATCH (e:Entity)
                RETURN e.type as entity_type, count(e) as count
                ORDER BY count DESC
            """,
            "count_relationships_by_type": """
                MATCH ()-[r]-()
                RETURN type(r) as relationship_type, count(r) as count
                ORDER BY count DESC
            """,
            # Full-text search queries
            "fulltext_search_entities": """
                CALL db.index.fulltext.queryNodes('entity_text_fulltext', $search_term)
                YIELD node, score
                RETURN node as entity, score
                ORDER BY score DESC
                LIMIT $limit
            """,
            "fulltext_search_documents": """
                CALL db.index.fulltext.queryNodes('document_content_fulltext', $search_term)
                YIELD node, score
                RETURN node as document, score
                ORDER BY score DESC
                LIMIT $limit
            """,
        }

    def execute_optimized_query(
        self,
        template_name: str,
        parameters: dict[str, Any],
        use_read_replica: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a pre-optimized query template with given parameters.

        Args:
            template_name: Name of the query template to use
            parameters: Parameters for the query
            use_read_replica: Whether to use read replica for read queries (Enterprise)

        Returns:
            Query results

        Raises:
            ValueError: If template name is not found
        """
        templates = self.get_optimized_query_templates()

        if template_name not in templates:
            available_templates = list(templates.keys())
            raise ValueError(
                f"Query template '{template_name}' not found. "
                f"Available templates: {available_templates}"
            )

        query = templates[template_name].strip()

        # Determine if this is a read or write query
        query_lower = query.lower()
        is_read_query = not any(
            keyword in query_lower
            for keyword in ["create", "merge", "set", "delete", "remove"]
        )

        # Use appropriate execution method
        if is_read_query and use_read_replica:
            return self.execute_read_query(query, parameters)
        else:
            return self.execute_query(query, parameters)

    def batch_execute_queries(
        self, queries: list[tuple[str, dict[str, Any]]], use_transaction: bool = True
    ) -> list[list[dict[str, Any]]]:
        """Execute multiple queries efficiently in batch.

        Args:
            queries: List of (query, parameters) tuples
            use_transaction: Whether to execute all queries in a single transaction

        Returns:
            List of results for each query
        """
        if not queries:
            return []

        results = []

        if use_transaction:
            # Execute all queries in a single transaction for consistency
            def _batch_tx(tx):
                batch_results = []
                for query, params in queries:
                    result = tx.run(query, params or {})
                    batch_results.append([record.data() for record in result])
                return batch_results

            try:
                with self.get_session() as session:
                    results = session.execute_write(_batch_tx)
            except Exception as e:
                logger.error("Batch query execution failed", extra={"error": str(e)})
                raise
        else:
            # Execute queries individually
            for query, params in queries:
                try:
                    result = self.execute_query(query, params)
                    results.append(result)
                except Exception as e:
                    logger.error(
                        "Individual query in batch failed",
                        extra={"error": str(e), "query": query[:100]},
                    )
                    results.append([])  # Empty result for failed query

        logger.info(
            "Batch query execution completed",
            extra={
                "query_count": len(queries),
                "use_transaction": use_transaction,
                "total_results": sum(len(r) for r in results),
            },
        )

        return results

    def optimize_query_for_performance(self, query: str) -> str:
        """Automatically optimize a query for better performance.

        Args:
            query: Original Cypher query

        Returns:
            Optimized query string
        """
        optimized = query.strip()

        # Add LIMIT if missing and query doesn't have aggregation
        if (
            "limit" not in optimized.lower()
            and "count(" not in optimized.lower()
            and "collect(" not in optimized.lower()
            and "return" in optimized.lower()
        ):
            # Add a reasonable default limit
            optimized += "\nLIMIT 1000"

        # Optimize MATCH patterns
        lines = optimized.split("\n")
        optimized_lines = []

        for line in lines:
            line_lower = line.lower().strip()

            # Add index hints for UUID lookups
            if "uuid:" in line_lower and "using index" not in line_lower:
                # This is a simplified optimization - in practice, you'd need more sophisticated parsing
                if "{uuid:" in line:
                    line += " USING INDEX"

            # Suggest WITH clauses for complex queries
            if (
                line_lower.startswith("match")
                and len([l for l in lines if l.lower().strip().startswith("match")]) > 2
            ):
                # For queries with multiple MATCH clauses, suggest using WITH for pipelining
                pass  # This would require more complex query parsing

            optimized_lines.append(line)

        optimized = "\n".join(optimized_lines)

        logger.debug(
            "Query optimization completed",
            extra={"original_length": len(query), "optimized_length": len(optimized)},
        )

        return optimized

    def prune_old_data(
        self,
        older_than_days: int = 30,
        node_types: list[str] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Prune old data from the graph based on age criteria.

        Args:
            older_than_days: Remove data older than this many days
            node_types: Specific node types to prune (None = all types)
            dry_run: If True, only count what would be deleted without actually deleting

        Returns:
            Dictionary containing pruning results and statistics
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        import time

        cutoff_timestamp = time.time() - (older_than_days * 24 * 60 * 60)

        results = {
            "dry_run": dry_run,
            "cutoff_timestamp": cutoff_timestamp,
            "older_than_days": older_than_days,
            "node_types": node_types,
            "nodes_pruned": 0,
            "relationships_pruned": 0,
            "errors": [],
        }

        try:
            # Build node type filter
            type_filter = ""
            if node_types:
                type_labels = " OR ".join(
                    [f"n:{node_type}" for node_type in node_types]
                )
                type_filter = f"AND ({type_labels})"

            # Count/delete old nodes
            if dry_run:
                count_query = f"""
                    MATCH (n)
                    WHERE n.created_at < $cutoff_timestamp {type_filter}
                    RETURN count(n) as node_count
                """
                count_result = self.execute_query(
                    count_query, {"cutoff_timestamp": cutoff_timestamp}
                )
                results["nodes_pruned"] = (
                    count_result[0]["node_count"] if count_result else 0
                )

                # Count relationships that would be deleted
                rel_count_query = f"""
                    MATCH (n)-[r]-()
                    WHERE n.created_at < $cutoff_timestamp {type_filter}
                    RETURN count(r) as rel_count
                """
                rel_count_result = self.execute_query(
                    rel_count_query, {"cutoff_timestamp": cutoff_timestamp}
                )
                results["relationships_pruned"] = (
                    rel_count_result[0]["rel_count"] if rel_count_result else 0
                )
            else:
                # Actually delete old data
                delete_query = f"""
                    MATCH (n)
                    WHERE n.created_at < $cutoff_timestamp {type_filter}
                    DETACH DELETE n
                    RETURN count(n) as deleted_count
                """
                delete_result = self.execute_write_transaction(
                    delete_query, {"cutoff_timestamp": cutoff_timestamp}
                )
                results["nodes_pruned"] = (
                    delete_result[0]["deleted_count"] if delete_result else 0
                )

                logger.info(
                    "Data pruning completed",
                    extra={
                        "nodes_deleted": results["nodes_pruned"],
                        "older_than_days": older_than_days,
                        "node_types": node_types,
                    },
                )

        except Exception as e:
            error_msg = f"Data pruning failed: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)

        return results

    def prune_orphaned_nodes(self, dry_run: bool = True) -> dict[str, Any]:
        """Remove nodes that have no relationships (orphaned nodes).

        Args:
            dry_run: If True, only count what would be deleted without actually deleting

        Returns:
            Dictionary containing pruning results
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        results = {
            "dry_run": dry_run,
            "orphaned_nodes_pruned": 0,
            "errors": [],
        }

        try:
            if dry_run:
                # Count orphaned nodes
                count_query = """
                    MATCH (n)
                    WHERE NOT (n)-[]-()
                    RETURN count(n) as orphan_count
                """
                count_result = self.execute_query(count_query)
                results["orphaned_nodes_pruned"] = (
                    count_result[0]["orphan_count"] if count_result else 0
                )
            else:
                # Delete orphaned nodes
                delete_query = """
                    MATCH (n)
                    WHERE NOT (n)-[]-()
                    DELETE n
                    RETURN count(n) as deleted_count
                """
                delete_result = self.execute_write_transaction(delete_query)
                results["orphaned_nodes_pruned"] = (
                    delete_result[0]["deleted_count"] if delete_result else 0
                )

                logger.info(
                    "Orphaned nodes pruning completed",
                    extra={"nodes_deleted": results["orphaned_nodes_pruned"]},
                )

        except Exception as e:
            error_msg = f"Orphaned nodes pruning failed: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)

        return results

    def prune_duplicate_relationships(self, dry_run: bool = True) -> dict[str, Any]:
        """Remove duplicate relationships between the same nodes.

        Args:
            dry_run: If True, only count what would be deleted without actually deleting

        Returns:
            Dictionary containing pruning results
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        results = {
            "dry_run": dry_run,
            "duplicate_relationships_pruned": 0,
            "errors": [],
        }

        try:
            if dry_run:
                # Count duplicate relationships
                count_query = """
                    MATCH (a)-[r1]->(b)
                    MATCH (a)-[r2]->(b)
                    WHERE id(r1) < id(r2) AND type(r1) = type(r2)
                    RETURN count(r2) as duplicate_count
                """
                count_result = self.execute_query(count_query)
                results["duplicate_relationships_pruned"] = (
                    count_result[0]["duplicate_count"] if count_result else 0
                )
            else:
                # Delete duplicate relationships (keep the first one)
                delete_query = """
                    MATCH (a)-[r1]->(b)
                    MATCH (a)-[r2]->(b)
                    WHERE id(r1) < id(r2) AND type(r1) = type(r2)
                    DELETE r2
                    RETURN count(r2) as deleted_count
                """
                delete_result = self.execute_write_transaction(delete_query)
                results["duplicate_relationships_pruned"] = (
                    delete_result[0]["deleted_count"] if delete_result else 0
                )

                logger.info(
                    "Duplicate relationships pruning completed",
                    extra={
                        "relationships_deleted": results[
                            "duplicate_relationships_pruned"
                        ]
                    },
                )

        except Exception as e:
            error_msg = f"Duplicate relationships pruning failed: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)

        return results

    def prune_low_quality_entities(
        self,
        min_relationship_count: int = 1,
        min_name_length: int = 2,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Remove low-quality entities based on various criteria.

        Args:
            min_relationship_count: Minimum number of relationships an entity should have
            min_name_length: Minimum length for entity names
            dry_run: If True, only count what would be deleted without actually deleting

        Returns:
            Dictionary containing pruning results
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        results = {
            "dry_run": dry_run,
            "low_quality_entities_pruned": 0,
            "criteria": {
                "min_relationship_count": min_relationship_count,
                "min_name_length": min_name_length,
            },
            "errors": [],
        }

        try:
            # Build quality criteria
            quality_conditions = []

            if min_relationship_count > 0:
                quality_conditions.append(f"size((e)-[]-()) < {min_relationship_count}")

            if min_name_length > 0:
                quality_conditions.append(f"size(e.name) < {min_name_length}")

            if not quality_conditions:
                results["errors"].append("No quality criteria specified")
                return results

            where_clause = " OR ".join(quality_conditions)

            if dry_run:
                # Count low-quality entities
                count_query = f"""
                    MATCH (e:Entity)
                    WHERE {where_clause}
                    RETURN count(e) as low_quality_count
                """
                count_result = self.execute_query(count_query)
                results["low_quality_entities_pruned"] = (
                    count_result[0]["low_quality_count"] if count_result else 0
                )
            else:
                # Delete low-quality entities
                delete_query = f"""
                    MATCH (e:Entity)
                    WHERE {where_clause}
                    DETACH DELETE e
                    RETURN count(e) as deleted_count
                """
                delete_result = self.execute_write_transaction(delete_query)
                results["low_quality_entities_pruned"] = (
                    delete_result[0]["deleted_count"] if delete_result else 0
                )

                logger.info(
                    "Low-quality entities pruning completed",
                    extra={
                        "entities_deleted": results["low_quality_entities_pruned"],
                        "criteria": results["criteria"],
                    },
                )

        except Exception as e:
            error_msg = f"Low-quality entities pruning failed: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)

        return results

    def comprehensive_data_pruning(
        self,
        older_than_days: int = 30,
        remove_orphans: bool = True,
        remove_duplicates: bool = True,
        remove_low_quality: bool = True,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Perform comprehensive data pruning with multiple strategies.

        Args:
            older_than_days: Remove data older than this many days
            remove_orphans: Whether to remove orphaned nodes
            remove_duplicates: Whether to remove duplicate relationships
            remove_low_quality: Whether to remove low-quality entities
            dry_run: If True, only analyze what would be deleted without actually deleting

        Returns:
            Dictionary containing comprehensive pruning results
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        start_time = time.time()

        comprehensive_results = {
            "dry_run": dry_run,
            "start_time": start_time,
            "strategies_applied": [],
            "total_nodes_pruned": 0,
            "total_relationships_pruned": 0,
            "errors": [],
        }

        try:
            # 1. Prune old data
            if older_than_days > 0:
                old_data_results = self.prune_old_data(
                    older_than_days=older_than_days, dry_run=dry_run
                )
                comprehensive_results["old_data_pruning"] = old_data_results
                comprehensive_results["strategies_applied"].append("old_data")
                comprehensive_results["total_nodes_pruned"] += old_data_results[
                    "nodes_pruned"
                ]
                comprehensive_results["total_relationships_pruned"] += old_data_results[
                    "relationships_pruned"
                ]
                comprehensive_results["errors"].extend(old_data_results["errors"])

            # 2. Remove orphaned nodes
            if remove_orphans:
                orphan_results = self.prune_orphaned_nodes(dry_run=dry_run)
                comprehensive_results["orphan_pruning"] = orphan_results
                comprehensive_results["strategies_applied"].append("orphans")
                comprehensive_results["total_nodes_pruned"] += orphan_results[
                    "orphaned_nodes_pruned"
                ]
                comprehensive_results["errors"].extend(orphan_results["errors"])

            # 3. Remove duplicate relationships
            if remove_duplicates:
                duplicate_results = self.prune_duplicate_relationships(dry_run=dry_run)
                comprehensive_results["duplicate_pruning"] = duplicate_results
                comprehensive_results["strategies_applied"].append("duplicates")
                comprehensive_results[
                    "total_relationships_pruned"
                ] += duplicate_results["duplicate_relationships_pruned"]
                comprehensive_results["errors"].extend(duplicate_results["errors"])

            # 4. Remove low-quality entities
            if remove_low_quality:
                quality_results = self.prune_low_quality_entities(dry_run=dry_run)
                comprehensive_results["quality_pruning"] = quality_results
                comprehensive_results["strategies_applied"].append("low_quality")
                comprehensive_results["total_nodes_pruned"] += quality_results[
                    "low_quality_entities_pruned"
                ]
                comprehensive_results["errors"].extend(quality_results["errors"])

            comprehensive_results["duration_ms"] = round(
                (time.time() - start_time) * 1000, 2
            )

            logger.info(
                "Comprehensive data pruning completed",
                extra={
                    "dry_run": dry_run,
                    "strategies": comprehensive_results["strategies_applied"],
                    "total_nodes_pruned": comprehensive_results["total_nodes_pruned"],
                    "total_relationships_pruned": comprehensive_results[
                        "total_relationships_pruned"
                    ],
                    "duration_ms": comprehensive_results["duration_ms"],
                },
            )

        except Exception as e:
            error_msg = f"Comprehensive data pruning failed: {str(e)}"
            comprehensive_results["errors"].append(error_msg)
            logger.error(error_msg)

        return comprehensive_results

    def get_pruning_recommendations(self) -> dict[str, Any]:
        """Analyze the graph and provide data pruning recommendations.

        Returns:
            Dictionary containing pruning recommendations and statistics
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        recommendations = {
            "analysis_timestamp": time.time(),
            "recommendations": [],
            "statistics": {},
            "errors": [],
        }

        try:
            # Analyze data age distribution
            age_query = """
                MATCH (n)
                WHERE n.created_at IS NOT NULL
                WITH n.created_at as created_at
                RETURN 
                    min(created_at) as oldest,
                    max(created_at) as newest,
                    avg(created_at) as average,
                    count(*) as total_with_timestamps
            """
            age_result = self.execute_query(age_query)
            if age_result:
                age_stats = age_result[0]
                recommendations["statistics"]["age_distribution"] = age_stats

                # Calculate age-based recommendations
                current_time = time.time()
                oldest_age_days = (current_time - age_stats["oldest"]) / (24 * 60 * 60)
                if oldest_age_days > 365:  # Older than 1 year
                    recommendations["recommendations"].append(
                        {
                            "type": "age_based_pruning",
                            "priority": "medium",
                            "description": f"Consider pruning data older than {int(oldest_age_days)} days",
                            "suggested_action": "Run prune_old_data() with appropriate age threshold",
                        }
                    )

            # Analyze orphaned nodes
            orphan_query = """
                MATCH (n)
                WHERE NOT (n)-[]-()
                RETURN count(n) as orphan_count
            """
            orphan_result = self.execute_query(orphan_query)
            if orphan_result:
                orphan_count = orphan_result[0]["orphan_count"]
                recommendations["statistics"]["orphaned_nodes"] = orphan_count
                if orphan_count > 100:
                    recommendations["recommendations"].append(
                        {
                            "type": "orphan_removal",
                            "priority": "high" if orphan_count > 1000 else "medium",
                            "description": f"Found {orphan_count} orphaned nodes that could be removed",
                            "suggested_action": "Run prune_orphaned_nodes()",
                        }
                    )

            # Analyze duplicate relationships
            duplicate_query = """
                MATCH (a)-[r1]->(b)
                MATCH (a)-[r2]->(b)
                WHERE id(r1) < id(r2) AND type(r1) = type(r2)
                RETURN count(r2) as duplicate_count
            """
            duplicate_result = self.execute_query(duplicate_query)
            if duplicate_result:
                duplicate_count = duplicate_result[0]["duplicate_count"]
                recommendations["statistics"][
                    "duplicate_relationships"
                ] = duplicate_count
                if duplicate_count > 10:
                    recommendations["recommendations"].append(
                        {
                            "type": "duplicate_removal",
                            "priority": "medium",
                            "description": f"Found {duplicate_count} duplicate relationships",
                            "suggested_action": "Run prune_duplicate_relationships()",
                        }
                    )

            # Analyze entity quality
            quality_query = """
                MATCH (e:Entity)
                RETURN 
                    count(e) as total_entities,
                    count(CASE WHEN size(e.name) < 3 THEN 1 END) as short_names,
                    count(CASE WHEN size((e)-[]-()) = 0 THEN 1 END) as no_relationships,
                    count(CASE WHEN size((e)-[]-()) = 1 THEN 1 END) as single_relationship
            """
            quality_result = self.execute_query(quality_query)
            if quality_result:
                quality_stats = quality_result[0]
                recommendations["statistics"]["entity_quality"] = quality_stats

                low_quality_count = (
                    quality_stats["short_names"] + quality_stats["no_relationships"]
                )
                if low_quality_count > 50:
                    recommendations["recommendations"].append(
                        {
                            "type": "quality_improvement",
                            "priority": "low",
                            "description": f"Found {low_quality_count} potentially low-quality entities",
                            "suggested_action": "Run prune_low_quality_entities() with appropriate criteria",
                        }
                    )

            logger.debug("Pruning recommendations analysis completed")

        except Exception as e:
            error_msg = f"Pruning recommendations analysis failed: {str(e)}"
            recommendations["errors"].append(error_msg)
            logger.error(error_msg)

        return recommendations

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
            logger.error("Error clearing Neo4j databasef", extra={"error": str(e)})
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

    def health_check(self) -> dict[str, Any]:
        """Perform health check of the Neo4j connection.

        Returns:
            Dictionary containing health status and metrics
        """
        try:
            if not self.is_connected:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": "Not connected to Neo4j",
                }

            # Test basic connectivity
            test_result = self.test_connection()

            if test_result:
                # Get database info
                db_info = self.get_database_info()

                return {
                    "status": "healthy",
                    "connected": True,
                    "database_info": db_info,
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": "Connection test failed",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }
