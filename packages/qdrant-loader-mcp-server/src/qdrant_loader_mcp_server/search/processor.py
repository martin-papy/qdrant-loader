"""Query processor for handling search queries."""

import re
from typing import Any

from openai import AsyncOpenAI

from ..config import OpenAIConfig
from ..utils.logging import LoggingConfig
from .nlp.spacy_analyzer import SpaCyQueryAnalyzer

class QueryProcessor:
    """Query processor for handling search queries with spaCy-powered intelligence."""

    def __init__(self, openai_config: OpenAIConfig):
        """Initialize the query processor."""
        self.openai_client: AsyncOpenAI | None = AsyncOpenAI(
            api_key=openai_config.api_key
        )
        self.logger = LoggingConfig.get_logger(__name__)
        
        # 🔥 NEW: Initialize spaCy analyzer for fast, local intent detection
        self.spacy_analyzer = SpaCyQueryAnalyzer(spacy_model="en_core_web_md")

    async def process_query(self, query: str) -> dict[str, Any]:
        """🔥 ENHANCED: Process a search query using spaCy for intelligent analysis.

        Args:
            query: The search query string

        Returns:
            Processed query information including intent and filters
        """
        try:
            # Clean and normalize query
            cleaned_query = self._clean_query(query)

            # Handle empty queries
            if not cleaned_query:
                return {
                    "query": cleaned_query,
                    "intent": "general",
                    "source_type": None,
                    "processed": False,
                }

            # 🔥 Use spaCy for fast, local intent inference
            intent, inference_failed = await self._infer_intent_spacy(cleaned_query)

            # Extract source type if present
            source_type = self._extract_source_type(cleaned_query, intent)

            return {
                "query": cleaned_query,
                "intent": intent,
                "source_type": source_type,
                "processed": not inference_failed,
                "uses_spacy": True,  # Indicate we used spaCy analysis
            }
        except Exception as e:
            self.logger.error("Query processing failed", error=str(e), query=query)
            # Return fallback response instead of raising exception
            return {
                "query": query,
                "intent": "general",
                "source_type": None,
                "processed": False,
                "uses_spacy": False,
            }

    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query.

        Args:
            query: The raw query string

        Returns:
            Cleaned query string
        """
        # Remove extra whitespace
        query = re.sub(r"\s+", " ", query.strip())
        return query

    async def _infer_intent_spacy(self, query: str) -> tuple[str, bool]:
        """🔥 NEW: Infer intent using spaCy linguistic analysis (fast and local).

        Args:
            query: The cleaned query string

        Returns:
            Tuple of (inferred intent, whether inference failed)
        """
        try:
            # Use spaCy analyzer for comprehensive query analysis
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)
            
            # Get primary intent from spaCy analysis
            primary_intent = query_analysis.intent_signals.get("primary_intent", "general")
            confidence = query_analysis.intent_signals.get("confidence", 0.0)
            
            # Map spaCy intents to our system's intent categories
            intent_mapping = {
                "technical_lookup": "code",
                "business_context": "documentation", 
                "vendor_evaluation": "documentation",
                "procedural": "documentation",
                "informational": "general",
            }
            
            # Map to our system's categories
            mapped_intent = intent_mapping.get(primary_intent, "general")
            
            # Use confidence to determine if we trust the intent
            if confidence < 0.3:
                mapped_intent = "general"
            
            self.logger.debug(
                "🔥 spaCy intent inference",
                query=query[:50],
                primary_intent=primary_intent,
                mapped_intent=mapped_intent,
                confidence=confidence,
                processing_time_ms=query_analysis.processing_time_ms,
            )
            
            return mapped_intent, False
            
        except Exception as e:
            self.logger.warning(f"spaCy intent inference failed: {e}")
            return "general", True

    async def _infer_intent(self, query: str) -> tuple[str, bool]:
        """🔥 LEGACY: Original OpenAI-based intent inference (kept as fallback).

        Args:
            query: The cleaned query string

        Returns:
            Tuple of (inferred intent, whether inference failed)
        """
        try:
            if self.openai_client is None:
                raise RuntimeError("OpenAI client not initialized")

            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a query intent classifier. Classify the query into one of these categories: code, documentation, issue, or general. Respond with just the category name.",
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0,
            )

            if not response.choices or not response.choices[0].message:
                return "general", False  # Default to general if no response

            content = response.choices[0].message.content
            if not content:
                return "general", False  # Default to general if empty content

            return content.strip().lower(), False
        except Exception as e:
            self.logger.error("Intent inference failed", error=str(e), query=query)
            return (
                "general",
                True,
            )  # Default to general if inference fails, mark as failed

    def _extract_source_type(self, query: str, intent: str) -> str | None:
        """🔥 ENHANCED: Extract source type using improved keyword matching.

        Args:
            query: The cleaned query string
            intent: The inferred intent

        Returns:
            Source type if found, None otherwise
        """
        # Enhanced source type keywords with more variations
        source_keywords = {
            "git": ["git", "code", "repository", "repo", "github", "gitlab", "bitbucket", "source"],
            "confluence": ["confluence", "doc", "documentation", "wiki", "page", "space"],
            "jira": ["jira", "issue", "ticket", "bug", "story", "task", "epic"],
            "localfile": ["localfile", "local", "file", "files", "filesystem", "disk", "folder", "directory"],
        }

        # Check for explicit source type mentions
        query_lower = query.lower()
        for source_type, keywords in source_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                self.logger.debug(f"🔥 Source type detected: {source_type}", query=query[:50])
                return source_type

        # 🔥 NEW: Intent-based source type inference
        if intent == "code":
            # Code-related queries likely target git repositories
            return "git"
        elif intent == "documentation" and any(word in query_lower for word in ["requirements", "spec", "design"]):
            # Documentation queries about requirements/design likely target confluence
            return "confluence"
        elif intent == "issue" or "issue" in query_lower:
            # Issue-related queries target jira
            return "jira"

        # Return None to search across all source types
        return None

    def get_analyzer_stats(self) -> dict[str, Any]:
        """🔥 NEW: Get spaCy analyzer statistics for monitoring."""
        try:
            return {
                "spacy_model": self.spacy_analyzer.spacy_model,
                "cache_stats": self.spacy_analyzer.get_cache_stats(),
            }
        except Exception as e:
            self.logger.warning(f"Failed to get analyzer stats: {e}")
            return {"error": str(e)}

    def clear_analyzer_cache(self):
        """🔥 NEW: Clear spaCy analyzer cache to free memory."""
        try:
            self.spacy_analyzer.clear_cache()
            self.logger.info("Cleared spaCy analyzer cache")
        except Exception as e:
            self.logger.warning(f"Failed to clear analyzer cache: {e}")
