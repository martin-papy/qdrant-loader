"""Enricher pipeline for orchestrating multiple metadata enrichers.

POC2-002: LlamaIndex-inspired enricher pipeline.

This module provides the EnricherPipeline class that coordinates running
multiple enrichers on documents. The pipeline handles:

1. Ordering enrichers by priority
2. Running enrichers in sequence or parallel
3. Aggregating results and merging metadata
4. Error handling and graceful degradation
5. Performance monitoring and logging
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .base_enricher import BaseEnricher, EnricherPriority, EnricherResult

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.core.document import Document

logger = LoggingConfig.get_logger(__name__)


@dataclass
class PipelineResult:
    """Result of running the entire enrichment pipeline.

    Attributes:
        success: Whether the pipeline completed (may have partial failures)
        merged_metadata: All metadata from successful enrichers
        enricher_results: Individual results from each enricher
        total_time_ms: Total pipeline execution time
        errors: Aggregated errors from all enrichers
    """

    success: bool = True
    merged_metadata: dict = field(default_factory=dict)
    enricher_results: dict[str, EnricherResult] = field(default_factory=dict)
    total_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    def get_successful_enrichers(self) -> list[str]:
        """Get names of enrichers that succeeded."""
        return [
            name for name, result in self.enricher_results.items()
            if result.success and not result.skipped
        ]

    def get_skipped_enrichers(self) -> list[str]:
        """Get names of enrichers that were skipped."""
        return [
            name for name, result in self.enricher_results.items()
            if result.skipped
        ]

    def get_failed_enrichers(self) -> list[str]:
        """Get names of enrichers that failed."""
        return [
            name for name, result in self.enricher_results.items()
            if not result.success
        ]


class EnricherPipeline:
    """Orchestrates running multiple enrichers on documents.

    The pipeline provides several execution modes:
    - Sequential: Run enrichers one after another (default)
    - Parallel: Run enrichers concurrently (for independent enrichers)

    Enrichers are automatically sorted by priority before execution.

    Example:
        pipeline = EnricherPipeline([
            EntityEnricher(settings),
            KeywordEnricher(settings),
        ])

        # Enrich a single document
        result = await pipeline.enrich(document)

        # Enrich multiple documents
        results = await pipeline.enrich_batch(documents)

        # Access enrichment results
        document.metadata.update(result.merged_metadata)
    """

    def __init__(
        self,
        enrichers: list[BaseEnricher] | None = None,
        parallel: bool = False,
        stop_on_error: bool = False,
    ):
        """Initialize the enricher pipeline.

        Args:
            enrichers: List of enrichers to run
            parallel: If True, run enrichers concurrently
            stop_on_error: If True, stop pipeline on first error
        """
        self._enrichers: list[BaseEnricher] = []
        self.parallel = parallel
        self.stop_on_error = stop_on_error
        self.logger = LoggingConfig.get_logger(self.__class__.__name__)

        if enrichers:
            for enricher in enrichers:
                self.add_enricher(enricher)

    @property
    def enrichers(self) -> list[BaseEnricher]:
        """Get enrichers sorted by priority."""
        return sorted(self._enrichers, key=lambda e: e.priority.value)

    def add_enricher(self, enricher: BaseEnricher) -> "EnricherPipeline":
        """Add an enricher to the pipeline.

        Args:
            enricher: The enricher to add

        Returns:
            Self for method chaining
        """
        if not isinstance(enricher, BaseEnricher):
            raise TypeError(f"Expected BaseEnricher, got {type(enricher)}")

        # Check for duplicate names
        existing_names = {e.name for e in self._enrichers}
        if enricher.name in existing_names:
            self.logger.warning(
                f"Enricher with name '{enricher.name}' already exists, replacing"
            )
            self._enrichers = [e for e in self._enrichers if e.name != enricher.name]

        self._enrichers.append(enricher)
        self.logger.debug(f"Added enricher: {enricher.name} (priority: {enricher.priority.name})")
        return self

    def remove_enricher(self, name: str) -> "EnricherPipeline":
        """Remove an enricher by name.

        Args:
            name: Name of the enricher to remove

        Returns:
            Self for method chaining
        """
        self._enrichers = [e for e in self._enrichers if e.name != name]
        return self

    def get_enricher(self, name: str) -> BaseEnricher | None:
        """Get an enricher by name.

        Args:
            name: Name of the enricher

        Returns:
            The enricher or None if not found
        """
        for enricher in self._enrichers:
            if enricher.name == name:
                return enricher
        return None

    async def enrich(self, document: "Document") -> PipelineResult:
        """Run all enrichers on a single document.

        Args:
            document: The document to enrich

        Returns:
            PipelineResult with aggregated results
        """
        start_time = time.time()
        result = PipelineResult()

        if not self._enrichers:
            self.logger.debug("No enrichers configured, skipping enrichment")
            result.total_time_ms = (time.time() - start_time) * 1000
            return result

        if self.parallel:
            result = await self._run_parallel(document)
        else:
            result = await self._run_sequential(document)

        result.total_time_ms = (time.time() - start_time) * 1000

        # Log summary
        successful = result.get_successful_enrichers()
        skipped = result.get_skipped_enrichers()
        failed = result.get_failed_enrichers()

        self.logger.debug(
            f"Enrichment pipeline completed in {result.total_time_ms:.1f}ms: "
            f"{len(successful)} succeeded, {len(skipped)} skipped, {len(failed)} failed"
        )

        return result

    async def _run_sequential(self, document: "Document") -> PipelineResult:
        """Run enrichers sequentially.

        Args:
            document: The document to enrich

        Returns:
            PipelineResult with aggregated results
        """
        result = PipelineResult()

        for enricher in self.enrichers:
            enricher_result = await self._run_single_enricher(enricher, document)
            result.enricher_results[enricher.name] = enricher_result

            if enricher_result.success and not enricher_result.skipped:
                # Merge metadata from successful enrichers
                result.merged_metadata.update(enricher_result.metadata)
            elif not enricher_result.success:
                result.errors.extend(enricher_result.errors)
                if self.stop_on_error:
                    result.success = False
                    self.logger.warning(
                        f"Pipeline stopped due to error in {enricher.name}"
                    )
                    break

        return result

    async def _run_parallel(self, document: "Document") -> PipelineResult:
        """Run enrichers in parallel.

        Note: Parallel execution is best for independent enrichers.
        Enrichers that depend on each other's output should use sequential mode.

        Args:
            document: The document to enrich

        Returns:
            PipelineResult with aggregated results
        """
        result = PipelineResult()

        # Group enrichers by priority
        priority_groups: dict[EnricherPriority, list[BaseEnricher]] = {}
        for enricher in self._enrichers:
            priority = enricher.priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(enricher)

        # Run each priority group in parallel, groups run sequentially
        for priority in sorted(priority_groups.keys(), key=lambda p: p.value):
            group = priority_groups[priority]
            tasks = [
                self._run_single_enricher(enricher, document)
                for enricher in group
            ]

            enricher_results = await asyncio.gather(*tasks, return_exceptions=True)

            for enricher, enricher_result in zip(group, enricher_results):
                if isinstance(enricher_result, Exception):
                    error_result = EnricherResult.error_result(str(enricher_result))
                    result.enricher_results[enricher.name] = error_result
                    result.errors.append(f"{enricher.name}: {enricher_result}")
                else:
                    result.enricher_results[enricher.name] = enricher_result
                    if enricher_result.success and not enricher_result.skipped:
                        result.merged_metadata.update(enricher_result.metadata)
                    elif not enricher_result.success:
                        result.errors.extend(enricher_result.errors)

            if self.stop_on_error and result.errors:
                result.success = False
                break

        return result

    async def _run_single_enricher(
        self,
        enricher: BaseEnricher,
        document: "Document",
    ) -> EnricherResult:
        """Run a single enricher with error handling.

        Args:
            enricher: The enricher to run
            document: The document to enrich

        Returns:
            EnricherResult from the enricher
        """
        start_time = time.time()

        # Check if enricher should process this document
        should_process, skip_reason = enricher.should_process(document)
        if not should_process:
            self.logger.debug(f"Skipping {enricher.name}: {skip_reason}")
            return EnricherResult.skipped_result(skip_reason or "unknown")

        try:
            # Run enrichment with timeout
            result = await asyncio.wait_for(
                enricher.enrich(document),
                timeout=enricher.config.timeout_seconds,
            )
            result.processing_time_ms = (time.time() - start_time) * 1000

            if result.success and not result.skipped:
                self.logger.debug(
                    f"Enricher {enricher.name} completed in {result.processing_time_ms:.1f}ms, "
                    f"added {len(result.metadata)} metadata fields"
                )

            return result

        except TimeoutError:
            self.logger.warning(
                f"Enricher {enricher.name} timed out after {enricher.config.timeout_seconds}s"
            )
            return EnricherResult.error_result(
                f"timeout after {enricher.config.timeout_seconds}s"
            )

        except Exception as e:
            self.logger.error(f"Enricher {enricher.name} failed: {e}", exc_info=True)
            return EnricherResult.error_result(str(e))

    async def enrich_batch(
        self,
        documents: list["Document"],
        concurrency: int = 5,
    ) -> list[PipelineResult]:
        """Enrich multiple documents with controlled concurrency.

        Args:
            documents: List of documents to enrich
            concurrency: Maximum concurrent document processing

        Returns:
            List of PipelineResult, one per document
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def enrich_with_semaphore(doc: "Document") -> PipelineResult:
            async with semaphore:
                return await self.enrich(doc)

        tasks = [enrich_with_semaphore(doc) for doc in documents]
        return await asyncio.gather(*tasks)

    async def shutdown(self) -> None:
        """Shutdown all enrichers and clean up resources."""
        self.logger.debug(f"Shutting down {len(self._enrichers)} enrichers")
        for enricher in self._enrichers:
            try:
                await enricher.shutdown()
            except Exception as e:
                self.logger.warning(f"Error shutting down {enricher.name}: {e}")

    def __repr__(self) -> str:
        enricher_names = [e.name for e in self.enrichers]
        return f"EnricherPipeline(enrichers={enricher_names}, parallel={self.parallel})"
