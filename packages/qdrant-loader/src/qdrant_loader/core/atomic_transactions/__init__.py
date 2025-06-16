"""
Atomic Transaction Package for QDrant-Neo4j Synchronization

This package provides atomic transaction management across QDrant and Neo4j databases,
ensuring ACID-like properties for distributed operations with rollback capabilities
and compensation logic for maintaining data consistency.
"""

from .atomic_manager import AtomicTransactionManager
from .base import DatabaseTransactionManager
from .context import TransactionContext
from .enums import OperationType, TransactionState
from .models import CompensationAction, DatabaseOperation, DistributedTransaction
from .neo4j_manager import Neo4jTransactionManager
from .qdrant_manager import QdrantTransactionManager

__all__ = [
    # Enums
    "OperationType",
    "TransactionState",
    # Models
    "CompensationAction",
    "DatabaseOperation",
    "DistributedTransaction",
    # Base classes
    "DatabaseTransactionManager",
    # Transaction managers
    "QdrantTransactionManager",
    "Neo4jTransactionManager",
    "AtomicTransactionManager",
    # Context
    "TransactionContext",
]
