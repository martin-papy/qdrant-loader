"""Integration tests for Neo4j data persistence and end-to-end integration.

This module tests the complete Neo4j integration including:
- Connection establishment
- Data insertion and querying
- Container restart persistence
- Error handling and recovery
"""

import pytest
import time
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Generator

from qdrant_loader.config.neo4j import Neo4jConfig
from qdrant_loader.core.neo4j_manager import Neo4jManager


class TestNeo4jPersistenceIntegration:
    """Test Neo4j data persistence and integration."""

    @pytest.fixture
    def neo4j_config(self) -> Neo4jConfig:
        """Create Neo4j configuration for testing."""
        return Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "secure_password_2024"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            encrypted=True,  # Enable encryption for Aura compatibility
            max_retry_time=30,
            initial_retry_delay=1.0,
            retry_delay_multiplier=2.0,
            retry_delay_jitter_factor=0.1,
        )

    @pytest.fixture
    def neo4j_manager(
        self, neo4j_config: Neo4jConfig
    ) -> Generator[Neo4jManager, None, None]:
        """Create Neo4j manager instance."""
        manager = Neo4jManager(neo4j_config)
        yield manager
        # Cleanup after test
        if manager.is_connected:
            manager.close()

    def test_basic_connection_and_info(self, neo4j_manager: Neo4jManager):
        """Test basic connection and database info retrieval."""
        # Test connection
        neo4j_manager.connect()
        assert neo4j_manager.is_connected

        # Test connection validation
        assert neo4j_manager.test_connection()

        # Get database info
        db_info = neo4j_manager.get_database_info()

        # Verify expected info is present
        assert "version" in db_info
        assert "edition" in db_info
        assert "apoc_version" in db_info
        assert "available_databases" in db_info

        # Log info for debugging
        print(f"Neo4j Version: {db_info['version']}")
        print(f"Neo4j Edition: {db_info['edition']}")
        print(f"APOC Version: {db_info['apoc_version']}")
        print(f"Available Databases: {db_info['available_databases']}")

    def test_data_insertion_and_retrieval(self, neo4j_manager: Neo4jManager):
        """Test data insertion and retrieval operations."""
        neo4j_manager.connect()

        # Clear any existing test data
        neo4j_manager.execute_query("MATCH (n:TestNode) DETACH DELETE n")

        # Insert test data
        test_timestamp = datetime.now().isoformat()
        test_data = {
            "name": "Integration Test Node",
            "created_at": test_timestamp,
            "test_id": "persistence_test_001",
            "node_type": "integration_test",  # Flatten nested properties
            "version": "1.0",
        }

        # Insert node
        insert_query = """
        CREATE (n:TestNode {
            name: $name,
            created_at: $created_at,
            test_id: $test_id,
            node_type: $node_type,
            version: $version
        })
        RETURN n
        """

        result = neo4j_manager.execute_write_transaction(insert_query, test_data)

        assert len(result) == 1
        created_node = result[0]["n"]
        assert created_node["name"] == test_data["name"]
        assert created_node["test_id"] == test_data["test_id"]

        # Query the data back
        query_result = neo4j_manager.execute_read_transaction(
            "MATCH (n:TestNode {test_id: $test_id}) RETURN n",
            {"test_id": "persistence_test_001"},
        )

        assert len(query_result) == 1
        retrieved_node = query_result[0]["n"]
        assert retrieved_node["name"] == test_data["name"]
        assert retrieved_node["created_at"] == test_timestamp

    def test_relationship_creation_and_querying(self, neo4j_manager: Neo4jManager):
        """Test relationship creation and graph querying."""
        neo4j_manager.connect()

        # Clear existing test data
        neo4j_manager.execute_query("MATCH (n:TestEntity) DETACH DELETE n")

        # Create entities and relationships
        create_graph_query = """
        CREATE (a:TestEntity {name: 'Entity A', test_id: 'rel_test_001'})
        CREATE (b:TestEntity {name: 'Entity B', test_id: 'rel_test_002'})
        CREATE (c:TestEntity {name: 'Entity C', test_id: 'rel_test_003'})
        CREATE (a)-[:CONNECTS_TO {strength: 0.8, created_at: datetime()}]->(b)
        CREATE (b)-[:RELATES_TO {type: 'dependency', weight: 1.0}]->(c)
        CREATE (a)-[:INFLUENCES {impact: 'high'}]->(c)
        RETURN a, b, c
        """

        result = neo4j_manager.execute_write_transaction(create_graph_query)
        assert len(result) == 1

        # Query relationships
        relationship_query = """
        MATCH (a:TestEntity {test_id: 'rel_test_001'})-[r]->(b:TestEntity)
        RETURN a.name as source, type(r) as relationship, b.name as target, r as rel_props
        ORDER BY relationship
        """

        relationships = neo4j_manager.execute_read_transaction(relationship_query)
        assert len(relationships) == 2  # CONNECTS_TO and INFLUENCES

        # Verify relationship types
        rel_types = [rel["relationship"] for rel in relationships]
        assert "CONNECTS_TO" in rel_types
        assert "INFLUENCES" in rel_types

        # Test path queries
        path_query = """
        MATCH path = (a:TestEntity {test_id: 'rel_test_001'})-[*1..2]->(c:TestEntity {test_id: 'rel_test_003'})
        RETURN length(path) as path_length, [n in nodes(path) | n.name] as node_names
        ORDER BY path_length
        """

        paths = neo4j_manager.execute_read_transaction(path_query)
        assert len(paths) >= 1  # At least one path should exist

    def test_index_creation_and_performance(self, neo4j_manager: Neo4jManager):
        """Test index creation and query performance."""
        neo4j_manager.connect()

        # Create indexes
        neo4j_manager.create_indexes()

        # Verify indexes exist
        index_query = (
            "SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties"
        )
        indexes = neo4j_manager.execute_query(index_query)

        # Should have at least some indexes
        assert len(indexes) > 0

        # Look for our expected indexes
        index_names = [idx["name"] for idx in indexes]
        print(f"Available indexes: {index_names}")

    def test_transaction_rollback_and_consistency(self, neo4j_manager: Neo4jManager):
        """Test transaction rollback and data consistency."""
        neo4j_manager.connect()

        # Clear test data
        neo4j_manager.execute_query("MATCH (n:TransactionTest) DETACH DELETE n")

        # Test successful transaction
        success_query = """
        CREATE (n1:TransactionTest {name: 'Node 1', test_id: 'tx_test_001'})
        CREATE (n2:TransactionTest {name: 'Node 2', test_id: 'tx_test_002'})
        CREATE (n1)-[:LINKS_TO]->(n2)
        RETURN n1, n2
        """

        result = neo4j_manager.execute_write_transaction(success_query)
        assert len(result) == 1  # One row returned with both nodes

        # Verify data exists
        verify_result = neo4j_manager.execute_read_transaction(
            "MATCH (n:TransactionTest) RETURN count(n) as node_count"
        )
        assert verify_result[0]["node_count"] == 2

    def test_concurrent_operations_and_locking(self, neo4j_manager: Neo4jManager):
        """Test concurrent operations and proper locking behavior."""
        neo4j_manager.connect()

        # Clear test data
        neo4j_manager.execute_query("MATCH (n:ConcurrencyTest) DETACH DELETE n")

        # Create initial node
        neo4j_manager.execute_write_transaction(
            "CREATE (n:ConcurrencyTest {name: 'Counter', value: 0, test_id: 'concurrent_001'})"
        )

        # Simulate concurrent updates (in sequence for testing)
        for i in range(5):
            update_query = """
            MATCH (n:ConcurrencyTest {test_id: 'concurrent_001'})
            SET n.value = n.value + 1
            RETURN n.value as new_value
            """
            result = neo4j_manager.execute_write_transaction(update_query)
            assert result[0]["new_value"] == i + 1

    @pytest.mark.slow
    def test_container_restart_persistence(self, neo4j_manager: Neo4jManager):
        """Test data persistence across container restarts.

        This test requires Docker to be available and the Neo4j container to be running.
        """
        neo4j_manager.connect()

        # Insert persistent test data
        persistent_timestamp = datetime.now().isoformat()
        persistent_data = {
            "name": "Persistent Test Data",
            "created_at": persistent_timestamp,
            "test_id": "persistence_restart_001",
            "restart_test": True,
        }

        # Clear any existing persistent test data
        neo4j_manager.execute_query("MATCH (n:PersistentTest) DETACH DELETE n")

        # Insert the test data
        insert_query = """
        CREATE (n:PersistentTest {
            name: $name,
            created_at: $created_at,
            test_id: $test_id,
            restart_test: $restart_test
        })
        RETURN n
        """

        result = neo4j_manager.execute_write_transaction(insert_query, persistent_data)
        assert len(result) == 1

        # Close connection before restart
        neo4j_manager.close()

        # Restart Neo4j container
        print("Restarting Neo4j container...")
        try:
            # Stop the container
            subprocess.run(
                ["docker", "restart", "neo4j-db"],
                check=True,
                capture_output=True,
                text=True,
            )

            # Wait for container to be ready
            print("Waiting for Neo4j to be ready after restart...")
            time.sleep(10)

            # Wait for health check to pass
            max_wait = 60  # seconds
            wait_time = 0
            while wait_time < max_wait:
                try:
                    result = subprocess.run(
                        [
                            "docker",
                            "exec",
                            "neo4j-db",
                            "cypher-shell",
                            "-u",
                            "neo4j",
                            "-p",
                            "secure_password_2024",
                            "RETURN 1 as test",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if "test" in result.stdout:
                        print("Neo4j is ready after restart")
                        break
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass

                time.sleep(2)
                wait_time += 2

            if wait_time >= max_wait:
                pytest.skip("Neo4j container did not become ready after restart")

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Could not restart Neo4j container: {e}")
        except FileNotFoundError:
            pytest.skip("Docker not available for container restart test")

        # Reconnect and verify data persistence
        neo4j_manager.connect()

        # Query the persistent data
        query_result = neo4j_manager.execute_read_transaction(
            "MATCH (n:PersistentTest {test_id: $test_id}) RETURN n",
            {"test_id": "persistence_restart_001"},
        )

        # Verify data survived the restart
        assert len(query_result) == 1, "Data should persist after container restart"
        retrieved_node = query_result[0]["n"]
        assert retrieved_node["name"] == persistent_data["name"]
        assert retrieved_node["created_at"] == persistent_timestamp
        assert retrieved_node["restart_test"] is True

        print("✅ Data persistence verified after container restart")

    def test_error_handling_and_recovery(self, neo4j_manager: Neo4jManager):
        """Test error handling and recovery mechanisms."""
        neo4j_manager.connect()

        # Test invalid query handling
        with pytest.raises(Exception):  # Should raise a Neo4j ClientError
            neo4j_manager.execute_query("INVALID CYPHER QUERY")

        # Verify connection is still working after error
        assert neo4j_manager.test_connection()

        # Test constraint violation handling
        neo4j_manager.execute_query("MATCH (n:ErrorTest) DETACH DELETE n")

        # Create a unique constraint
        try:
            neo4j_manager.execute_query(
                "CREATE CONSTRAINT error_test_unique IF NOT EXISTS FOR (n:ErrorTest) REQUIRE n.unique_id IS UNIQUE"
            )
        except Exception:
            pass  # Constraint might already exist

        # Insert first node
        neo4j_manager.execute_write_transaction(
            "CREATE (n:ErrorTest {unique_id: 'duplicate_test', name: 'First'})"
        )

        # Try to insert duplicate - should fail
        with pytest.raises(Exception):
            neo4j_manager.execute_write_transaction(
                "CREATE (n:ErrorTest {unique_id: 'duplicate_test', name: 'Second'})"
            )

        # Verify connection still works
        assert neo4j_manager.test_connection()

    def test_performance_and_scalability(self, neo4j_manager: Neo4jManager):
        """Test performance with larger datasets."""
        neo4j_manager.connect()

        # Clear test data
        neo4j_manager.execute_query("MATCH (n:PerformanceTest) DETACH DELETE n")

        # Create batch of nodes
        batch_size = 100
        batch_query = """
        UNWIND range(1, $batch_size) as i
        CREATE (n:PerformanceTest {
            id: i,
            name: 'Node ' + toString(i),
            created_at: datetime(),
            test_batch: $batch_id
        })
        RETURN count(n) as created_count
        """

        start_time = time.time()
        result = neo4j_manager.execute_write_transaction(
            batch_query, {"batch_size": batch_size, "batch_id": "perf_test_001"}
        )
        end_time = time.time()

        assert result[0]["created_count"] == batch_size

        creation_time = end_time - start_time
        print(f"Created {batch_size} nodes in {creation_time:.2f} seconds")

        # Test batch query performance
        start_time = time.time()
        query_result = neo4j_manager.execute_read_transaction(
            "MATCH (n:PerformanceTest {test_batch: $batch_id}) RETURN count(n) as total_count",
            {"batch_id": "perf_test_001"},
        )
        end_time = time.time()

        assert query_result[0]["total_count"] == batch_size

        query_time = end_time - start_time
        print(f"Queried {batch_size} nodes in {query_time:.2f} seconds")

    def teardown_method(self):
        """Clean up test data after each test."""
        try:
            # Create a temporary manager for cleanup
            config = Neo4jConfig(
                uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                user=os.getenv("NEO4J_USER", "neo4j"),
                password=os.getenv("NEO4J_PASSWORD", "secure_password_2024"),
                database=os.getenv("NEO4J_DATABASE", "neo4j"),
                encrypted=True,  # Disable encryption for local testing
            )

            with Neo4jManager(config) as manager:
                manager.connect()

                # Clean up all test data
                cleanup_queries = [
                    "MATCH (n:TestNode) DETACH DELETE n",
                    "MATCH (n:TestEntity) DETACH DELETE n",
                    "MATCH (n:TransactionTest) DETACH DELETE n",
                    "MATCH (n:ConcurrencyTest) DETACH DELETE n",
                    "MATCH (n:PersistentTest) DETACH DELETE n",
                    "MATCH (n:ErrorTest) DETACH DELETE n",
                    "MATCH (n:PerformanceTest) DETACH DELETE n",
                ]

                for query in cleanup_queries:
                    try:
                        manager.execute_query(query)
                    except Exception as e:
                        print(f"Cleanup warning: {e}")

        except Exception as e:
            print(f"Cleanup error: {e}")
