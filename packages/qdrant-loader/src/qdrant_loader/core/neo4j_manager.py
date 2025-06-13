"""Neo4j database manager.

This module provides a manager class for Neo4j database operations,
including connection management and basic graph operations.
"""

from typing import Any, Dict, List, Optional, cast

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, ConfigurationError

from ..config import Neo4jConfig
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class Neo4jManager:
    """Manager for Neo4j database operations."""

    def __init__(self, config: Neo4jConfig):
        """Initialize the Neo4j manager.

        Args:
            config: Neo4j configuration settings
        """
        self.config = config
        self._driver: Optional[Driver] = None
        self._is_connected = False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self) -> None:
        """Establish connection to Neo4j database."""
        if self._driver is not None:
            logger.debug("Neo4j driver already initialized")
            return

        try:
            logger.info("Connecting to Neo4j database", extra={"uri": self.config.uri})

            # Get driver configuration from config
            driver_config = self.config.get_driver_config()

            # Validate trust parameter
            trust_value = driver_config.get(
                "trust", "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES"
            )
            if trust_value not in [
                "TRUST_ALL_CERTIFICATES",
                "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES",
            ]:
                trust_value = "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES"
                driver_config["trust"] = trust_value

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
            raise
        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailable", extra={"error": str(e)})
            raise
        except ConfigurationError as e:
            logger.error("Neo4j configuration error", extra={"error": str(e)})
            raise
        except Exception as e:
            logger.error(
                "Unexpected error connecting to Neo4j", extra={"error": str(e)}
            )
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
        self, database: Optional[str] = None, access_mode: Optional[str] = None
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

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        access_mode: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
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

    def execute_write_transaction(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
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

    def execute_read_transaction(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
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

    def get_database_info(self) -> Dict[str, Any]:
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
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
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
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a write query (Enterprise: routes to write instances).

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            List of result records as dictionaries
        """
        return self.execute_query(query, parameters, database, access_mode="WRITE")
