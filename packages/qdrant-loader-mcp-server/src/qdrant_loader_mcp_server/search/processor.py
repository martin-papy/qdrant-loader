"""Query processor for handling search queries."""

import re
from typing import Any

from openai import AsyncOpenAI

from ..config import OpenAIConfig
from ..utils.logging import LoggingConfig


class QueryProcessor:
    """Query processor for handling search queries."""

    def __init__(self, openai_config: OpenAIConfig):
        """Initialize the query processor."""
        self.openai_client: AsyncOpenAI | None = AsyncOpenAI(
            api_key=openai_config.api_key
        )
        self.logger = LoggingConfig.get_logger(__name__)

    async def process_query(self, query: str) -> dict[str, Any]:
        """Process a search query.

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

            # Infer query intent
            intent, inference_failed = await self._infer_intent(cleaned_query)

            # Extract source type if present
            source_type = self._extract_source_type(cleaned_query, intent)

            return {
                "query": cleaned_query,
                "intent": intent,
                "source_type": source_type,
                "processed": not inference_failed,
            }
        except Exception as e:
            self.logger.error("Query processing failed", error=str(e), query=query)
            # Return fallback response instead of raising exception
            return {
                "query": query,
                "intent": "general",
                "source_type": None,
                "processed": False,
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

    async def _infer_intent(self, query: str) -> tuple[str, bool]:
        """Infer the intent of the query using OpenAI.

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
        """Extract source type from query and intent.

        Args:
            query: The cleaned query string
            intent: The inferred intent

        Returns:
            Source type if found, None otherwise
        """
        # Check for explicit source type mentions
        source_keywords = {
            "git": ["git", "code", "repository", "repo"],
            "confluence": ["confluence", "doc", "documentation", "wiki"],
            "jira": ["jira", "issue", "ticket", "bug"],
            "localfile": ["localfile", "local", "file", "files", "filesystem", "disk"],
        }

        # Check for explicit source type mentions
        query_lower = query.lower()
        for source_type, keywords in source_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return source_type

        # Return None to search across all source types
        return None
