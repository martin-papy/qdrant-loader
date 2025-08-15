"""
Hybrid search package providing modular search pipeline components.

This package contains the complete hybrid search implementation with modular architecture:
- engine: Main HybridSearchEngine class  
- models: Data types and constants
- adapters: Component adapters for pipeline integration
- pipeline: Modular search pipeline orchestration
- interfaces: Abstract interfaces for components
"""

# Re-export the HybridSearchEngine for easy access
from .engine import HybridSearchEngine

__all__ = ["HybridSearchEngine"]


