"""
Intent Classification Package for Search Enhancement.

This package contains the complete intent classification and adaptive search functionality
with modular architecture for better maintainability and testability.

Architecture:
- models: Core data types (IntentType, SearchIntent, AdaptiveSearchConfig)
- classifier: Main IntentClassifier implementation with spaCy analysis
- strategy: AdaptiveSearchStrategy for intent-based configuration
"""

# Re-export core components for easy access
from .classifier import IntentClassifier
from .models import AdaptiveSearchConfig, IntentType, SearchIntent
from .strategy import AdaptiveSearchStrategy

__all__ = [
    "IntentType",
    "SearchIntent",
    "AdaptiveSearchConfig",
    "IntentClassifier",
    "AdaptiveSearchStrategy",
]
