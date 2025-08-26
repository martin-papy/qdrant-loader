"""
Intent-Aware Adaptive Search for Search Enhancement - Re-export Module.

This module provides the complete intent classification and adaptive search
functionality through a clean, modular architecture. All components have been
extracted to the intent/ package for better maintainability and testability.

Architecture:
- intent.models: Core data types (IntentType, SearchIntent, AdaptiveSearchConfig)
- intent.classifier: Main IntentClassifier implementation with spaCy analysis
- intent.strategy: AdaptiveSearchStrategy for intent-based configuration
"""

# Re-export core components from the intent package
from .intent import (
    AdaptiveSearchConfig,
    AdaptiveSearchStrategy,
    IntentClassifier,
    IntentType,
    SearchIntent,
)

# Convenient access to classes for backward compatibility
__all__ = [
    "IntentType",
    "SearchIntent",
    "AdaptiveSearchConfig",
    "IntentClassifier",
    "AdaptiveSearchStrategy",
]
