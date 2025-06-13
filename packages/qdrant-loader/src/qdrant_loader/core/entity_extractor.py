"""Entity extraction module using Graphiti for LLM-based entity and relationship extraction."""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import weakref

from graphiti_core.nodes import EpisodeType

from .graphiti_manager import GraphitiManager
from .prompts import EntityPromptManager
from .prompts.entity_prompts import PromptDomain
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class EntityType(Enum):
    """Supported entity types for extraction."""

    SERVICE = "Service"
    DATABASE = "Database"
    TEAM = "Team"
    PERSON = "Person"
    ORGANIZATION = "Organization"
    PROJECT = "Project"
    CONCEPT = "Concept"
    TECHNOLOGY = "Technology"
    API = "API"
    ENDPOINT = "Endpoint"


@dataclass
class ExtractedEntity:
    """Container for extracted entity information."""

    name: str
    entity_type: EntityType
    confidence: float = 0.0
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Container for entity extraction results."""

    entities: List[ExtractedEntity] = field(default_factory=list)
    processing_time: float = 0.0
    source_text: str = ""
    episode_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionTask:
    """Container for async extraction task information."""

    task_id: str
    text: str
    source_description: Optional[str] = None
    reference_time: Optional[datetime] = None
    domain: Optional[PromptDomain] = None
    custom_prompt: str = ""
    use_custom_prompts: bool = True
    priority: int = 0  # Higher numbers = higher priority
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ProcessingProgress:
    """Container for tracking processing progress."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    in_progress_tasks: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100.0

    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()


@dataclass
class ExtractionConfig:
    """Configuration for entity extraction."""

    enabled_entity_types: List[EntityType] = field(
        default_factory=lambda: list(EntityType)
    )
    batch_size: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 3600  # seconds
    max_text_length: int = 10000
    confidence_threshold: float = 0.5
    enable_caching: bool = True

    # Enhanced async processing configuration
    max_concurrent_extractions: int = 5  # Semaphore limit
    queue_max_size: int = 1000  # Max items in processing queue
    worker_pool_size: int = 3  # Number of worker coroutines
    enable_background_processing: bool = True
    progress_callback_interval: float = 1.0  # Seconds between progress updates
    task_timeout: float = 300.0  # Task timeout in seconds
    enable_streaming: bool = False  # Enable streaming for large datasets


class EntityExtractor:
    """Entity extractor using Graphiti's LLM-based extraction."""

    def __init__(
        self,
        graphiti_manager: GraphitiManager,
        config: Optional[ExtractionConfig] = None,
        prompt_manager: Optional[EntityPromptManager] = None,
    ):
        """Initialize the entity extractor.

        Args:
            graphiti_manager: Initialized GraphitiManager instance
            config: Extraction configuration (uses defaults if not provided)
            prompt_manager: Prompt manager for custom prompts (creates default if not provided)
        """
        self.graphiti_manager = graphiti_manager
        self.config = config or ExtractionConfig()
        self.prompt_manager = prompt_manager or EntityPromptManager()
        self._cache: Dict[str, ExtractionResult] = {}
        self._cache_timestamps: Dict[str, float] = {}

        # Enhanced async processing components
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_extractions)
        self._task_queue: asyncio.Queue[ExtractionTask] = asyncio.Queue(
            maxsize=self.config.queue_max_size
        )
        self._result_futures: Dict[str, asyncio.Future[ExtractionResult]] = {}
        self._background_workers: List[asyncio.Task] = []
        self._worker_shutdown_event = asyncio.Event()
        self._progress_callbacks: List[Callable[[ProcessingProgress], None]] = []
        self._current_progress = ProcessingProgress()
        self._progress_task: Optional[asyncio.Task] = None

        # Thread pool for CPU-intensive operations
        self._thread_pool = ThreadPoolExecutor(max_workers=2)

        # Weak reference tracking for cleanup
        self._active_tasks: weakref.WeakSet = weakref.WeakSet()

        # Statistics tracking
        self._stats = {
            "total_extractions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failed_extractions": 0,
            "total_entities_extracted": 0,
            "concurrent_extractions": 0,
            "queue_size": 0,
            "background_tasks_processed": 0,
        }

        logger.info(
            f"EntityExtractor initialized with {len(self.config.enabled_entity_types)} enabled entity types, "
            f"max concurrent: {self.config.max_concurrent_extractions}, "
            f"worker pool size: {self.config.worker_pool_size}"
        )

        # Start background workers if enabled
        if self.config.enable_background_processing:
            self._start_background_workers()

    def _start_background_workers(self) -> None:
        """Start background worker coroutines for processing queued tasks."""
        logger.info(f"Starting {self.config.worker_pool_size} background workers")

        for i in range(self.config.worker_pool_size):
            worker_task = asyncio.create_task(
                self._background_worker(worker_id=i),
                name=f"entity_extractor_worker_{i}",
            )
            self._background_workers.append(worker_task)
            self._active_tasks.add(worker_task)

    async def _background_worker(self, worker_id: int) -> None:
        """Background worker coroutine for processing queued extraction tasks.

        Args:
            worker_id: Unique identifier for this worker
        """
        logger.debug(f"Background worker {worker_id} started")

        while not self._worker_shutdown_event.is_set():
            try:
                # Wait for a task with timeout to allow periodic shutdown checks
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)

                logger.debug(f"Worker {worker_id} processing task {task.task_id}")
                self._current_progress.in_progress_tasks += 1
                self._stats["queue_size"] = self._task_queue.qsize()

                # Process the task
                try:
                    result = await self._process_extraction_task(task)

                    # Store result if there's a waiting future
                    if task.task_id in self._result_futures:
                        future = self._result_futures[task.task_id]
                        if not future.done():
                            future.set_result(result)
                        del self._result_futures[task.task_id]

                    self._current_progress.completed_tasks += 1
                    self._stats["background_tasks_processed"] += 1

                except Exception as e:
                    logger.error(
                        f"Worker {worker_id} failed to process task {task.task_id}: {e}"
                    )

                    # Set exception on future if waiting
                    if task.task_id in self._result_futures:
                        future = self._result_futures[task.task_id]
                        if not future.done():
                            future.set_exception(e)
                        del self._result_futures[task.task_id]

                    self._current_progress.failed_tasks += 1
                    self._stats["failed_extractions"] += 1

                finally:
                    self._current_progress.in_progress_tasks -= 1
                    self._task_queue.task_done()

            except asyncio.TimeoutError:
                # Timeout waiting for task - continue to check shutdown
                continue
            except Exception as e:
                logger.error(f"Background worker {worker_id} encountered error: {e}")
                await asyncio.sleep(1.0)  # Brief pause before retrying

        logger.debug(f"Background worker {worker_id} shutting down")

    async def _process_extraction_task(self, task: ExtractionTask) -> ExtractionResult:
        """Process a single extraction task with timeout and semaphore control.

        Args:
            task: The extraction task to process

        Returns:
            ExtractionResult from the extraction
        """
        async with self._semaphore:
            self._stats["concurrent_extractions"] += 1

            try:
                # Apply task timeout
                result = await asyncio.wait_for(
                    self.extract_entities(
                        text=task.text,
                        source_description=task.source_description,
                        reference_time=task.reference_time,
                        domain=task.domain,
                        custom_prompt=task.custom_prompt,
                        use_custom_prompts=task.use_custom_prompts,
                    ),
                    timeout=self.config.task_timeout,
                )

                return result

            except asyncio.TimeoutError:
                logger.error(
                    f"Task {task.task_id} timed out after {self.config.task_timeout}s"
                )
                raise
            finally:
                self._stats["concurrent_extractions"] -= 1

    async def extract_entities(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
        use_custom_prompts: bool = True,
    ) -> ExtractionResult:
        """Extract entities from text using Graphiti.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction
            domain: Domain for prompt selection (defaults to SOFTWARE_DEVELOPMENT)
            custom_prompt: Additional custom instructions for extraction
            use_custom_prompts: Whether to use custom domain-specific prompts

        Returns:
            ExtractionResult containing extracted entities
        """
        start_time = time.time()

        # Validate input
        if not text or not text.strip():
            logger.warning("Empty text provided for entity extraction")
            return ExtractionResult(
                source_text=text,
                processing_time=time.time() - start_time,
                errors=["Empty text provided"],
            )

        # Truncate text if too long
        if len(text) > self.config.max_text_length:
            logger.warning(
                f"Text too long ({len(text)} chars), truncating to {self.config.max_text_length}"
            )
            text = text[: self.config.max_text_length]

        # Check cache first
        cache_key = self._generate_cache_key(text, source_description)
        if self.config.enable_caching:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self._stats["cache_hits"] += 1
                logger.debug(f"Cache hit for extraction: {cache_key[:16]}...")
                return cached_result

        self._stats["cache_misses"] += 1
        self._stats["total_extractions"] += 1

        # Perform extraction with retry logic
        result = await self._extract_with_retry(
            text,
            source_description,
            reference_time,
            domain,
            custom_prompt,
            use_custom_prompts,
        )

        # Cache the result
        if self.config.enable_caching and not result.errors:
            self._store_in_cache(cache_key, result)

        # Update statistics
        self._stats["total_entities_extracted"] += len(result.entities)

        result.processing_time = time.time() - start_time
        logger.info(
            f"Extracted {len(result.entities)} entities in {result.processing_time:.2f}s"
        )

        return result

    async def extract_entities_batch(
        self,
        texts: List[str],
        source_descriptions: Optional[List[str]] = None,
        reference_times: Optional[List[datetime]] = None,
    ) -> List[ExtractionResult]:
        """Extract entities from multiple texts in batches with enhanced async processing.

        Args:
            texts: List of texts to extract entities from
            source_descriptions: Optional list of source descriptions
            reference_times: Optional list of reference times

        Returns:
            List of ExtractionResult objects
        """
        if not texts:
            return []

        logger.info(f"Starting enhanced batch entity extraction for {len(texts)} texts")

        # Prepare arguments - create proper lists with correct types
        actual_source_descriptions: List[Optional[str]] = []
        if source_descriptions is not None:
            actual_source_descriptions = [desc for desc in source_descriptions]
        else:
            actual_source_descriptions = [None] * len(texts)

        actual_reference_times: List[Optional[datetime]] = []
        if reference_times is not None:
            actual_reference_times = [time_ref for time_ref in reference_times]
        else:
            actual_reference_times = [None] * len(texts)

        # Process in batches with semaphore control
        results = []
        batch_size = self.config.batch_size

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_sources = actual_source_descriptions[i : i + batch_size]
            batch_times = actual_reference_times[i : i + batch_size]

            logger.debug(
                f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} "
                f"with semaphore control (max concurrent: {self.config.max_concurrent_extractions})"
            )

            # Create semaphore-controlled extraction tasks
            async def extract_with_semaphore(
                text: str, source: Optional[str], time_ref: Optional[datetime]
            ) -> ExtractionResult:
                async with self._semaphore:
                    self._stats["concurrent_extractions"] += 1
                    try:
                        return await self.extract_entities(text, source, time_ref)
                    finally:
                        self._stats["concurrent_extractions"] -= 1

            # Process batch concurrently with semaphore control
            batch_tasks = [
                extract_with_semaphore(text, source, time_ref)
                for text, source, time_ref in zip(
                    batch_texts, batch_sources, batch_times
                )
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch extraction failed for text {i+j}: {result}")
                    error_result = ExtractionResult(
                        source_text=batch_texts[j],
                        errors=[f"Extraction failed: {str(result)}"],
                    )
                    results.append(error_result)
                    self._stats["failed_extractions"] += 1
                else:
                    results.append(result)

        logger.info(f"Enhanced batch extraction completed: {len(results)} results")
        return results

    async def _extract_with_retry(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
        use_custom_prompts: bool = True,
    ) -> ExtractionResult:
        """Extract entities with retry logic.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction

        Returns:
            ExtractionResult containing extracted entities
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await self._perform_extraction(
                    text,
                    source_description,
                    reference_time,
                    domain,
                    custom_prompt,
                    use_custom_prompts,
                )
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (
                        2**attempt
                    )  # Exponential backoff
                    logger.warning(
                        f"Extraction attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_retries + 1} extraction attempts failed"
                    )

        # All retries failed
        self._stats["failed_extractions"] += 1
        return ExtractionResult(
            source_text=text,
            errors=[
                f"Extraction failed after {self.config.max_retries + 1} attempts: {str(last_exception)}"
            ],
        )

    async def _perform_extraction(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
        use_custom_prompts: bool = True,
    ) -> ExtractionResult:
        """Perform the actual entity extraction using Graphiti.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction
            domain: Domain for prompt selection
            custom_prompt: Additional custom instructions for extraction
            use_custom_prompts: Whether to use custom domain-specific prompts

        Returns:
            ExtractionResult containing extracted entities
        """
        if not self.graphiti_manager.is_initialized:
            raise RuntimeError("GraphitiManager is not initialized")

        # Use custom prompts if enabled and available
        if use_custom_prompts and self.prompt_manager:
            try:
                return await self._perform_custom_prompt_extraction(
                    text, source_description, reference_time, domain, custom_prompt
                )
            except Exception as e:
                logger.warning(
                    f"Custom prompt extraction failed, falling back to default: {e}"
                )

        # Add episode to Graphiti for entity extraction
        episode_id = await self.graphiti_manager.add_episode(
            name=f"Entity extraction - {datetime.now(timezone.utc).isoformat()}",
            content=text,
            episode_type=EpisodeType.text,
            source_description=source_description or "Entity extraction source",
            reference_time=reference_time or datetime.now(timezone.utc),
        )

        # Wait a moment for Graphiti to process the episode and extract entities
        await asyncio.sleep(0.5)

        # Retrieve entities from the episode using the new search-based method
        try:
            # First try to get entities specifically from this episode
            entity_type_strings = [et.value for et in self.config.enabled_entity_types]
            nodes = await self.graphiti_manager.get_entities_from_episode(
                episode_id, entity_type_strings
            )

            # If no entities found from episode search, try a broader search with the text content
            if not nodes:
                logger.debug(
                    "No entities found from episode search, trying content-based search"
                )
                # Use key terms from the text for search
                search_terms = self._extract_search_terms(text)
                nodes = await self.graphiti_manager.search_entities(
                    query=search_terms, entity_types=entity_type_strings, limit=50
                )

        except Exception as e:
            logger.warning(f"Failed to retrieve entities from Graphiti: {e}")
            # Fallback to general node search
            nodes = await self.graphiti_manager.get_nodes(limit=50)

        entities = self._convert_nodes_to_entities(nodes, text)

        return ExtractionResult(
            entities=entities,
            source_text=text,
            episode_id=episode_id,
            metadata={
                "source_description": source_description,
                "reference_time": (
                    reference_time.isoformat() if reference_time else None
                ),
                "graphiti_episode_id": episode_id,
                "extraction_method": "graphiti_episode",
            },
        )

    def _extract_search_terms(self, text: str, max_terms: int = 5) -> str:
        """Extract key search terms from text for entity search.

        Args:
            text: Input text to extract terms from
            max_terms: Maximum number of terms to extract

        Returns:
            Space-separated search terms
        """
        # Simple keyword extraction - could be enhanced with NLP
        import re

        # Remove common words and extract meaningful terms
        words = re.findall(r"\b[A-Za-z]{3,}\b", text.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "its",
            "may",
            "new",
            "now",
            "old",
            "see",
            "two",
            "who",
            "boy",
            "did",
            "she",
            "use",
            "way",
            "will",
            "with",
            "this",
            "that",
            "have",
            "from",
            "they",
            "know",
            "want",
            "been",
            "good",
            "much",
            "some",
            "time",
            "very",
            "when",
            "come",
            "here",
            "just",
            "like",
            "long",
            "make",
            "many",
            "over",
            "such",
            "take",
            "than",
            "them",
            "well",
            "were",
        }

        meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]

        # Take the first max_terms unique words
        unique_terms = list(dict.fromkeys(meaningful_words))[:max_terms]

        return " ".join(unique_terms) if unique_terms else text[:50]

    def _convert_nodes_to_entities(
        self, nodes: List[Any], source_text: str
    ) -> List[ExtractedEntity]:
        """Convert Graphiti nodes to ExtractedEntity objects.

        Args:
            nodes: List of Graphiti nodes
            source_text: Original source text

        Returns:
            List of ExtractedEntity objects
        """
        entities = []

        for node in nodes:
            try:
                # Handle different node types from Graphiti search results
                # Graphiti search can return different types of objects

                # Extract basic node information
                if hasattr(node, "name"):
                    entity_name = node.name
                elif hasattr(node, "title"):
                    entity_name = node.title
                elif hasattr(node, "content"):
                    # For episode nodes, extract a meaningful name from content
                    entity_name = (
                        str(node.content)[:50] + "..."
                        if len(str(node.content)) > 50
                        else str(node.content)
                    )
                else:
                    entity_name = str(node)[:50]

                # Determine entity type
                entity_type = EntityType.CONCEPT  # Default fallback

                # Try to extract entity type from various possible attributes
                if hasattr(node, "entity_type"):
                    try:
                        entity_type = EntityType(node.entity_type)
                    except ValueError:
                        pass
                elif hasattr(node, "type"):
                    try:
                        entity_type = EntityType(node.type)
                    except ValueError:
                        pass
                elif hasattr(node, "labels") and node.labels:
                    # Neo4j nodes have labels
                    for label in node.labels:
                        try:
                            entity_type = EntityType(label)
                            break
                        except ValueError:
                            continue

                # Check if this entity type is enabled
                if entity_type not in self.config.enabled_entity_types:
                    continue

                # Extract confidence score
                confidence = 0.8  # Default confidence
                if hasattr(node, "confidence"):
                    confidence = float(node.confidence)
                elif hasattr(node, "score"):
                    confidence = float(node.score)
                elif hasattr(node, "relevance"):
                    confidence = float(node.relevance)

                # Extract context information
                context = ""
                if hasattr(node, "context"):
                    context = str(node.context)
                elif hasattr(node, "description"):
                    context = str(node.description)
                elif hasattr(node, "content"):
                    context = str(node.content)[:200]  # Truncate long content

                # Build metadata from available node attributes
                metadata = {}

                # Common attributes to extract
                for attr in [
                    "uuid",
                    "id",
                    "created_at",
                    "updated_at",
                    "source",
                    "episode_id",
                ]:
                    if hasattr(node, attr):
                        metadata[attr] = getattr(node, attr)

                # Handle Neo4j specific attributes
                if hasattr(node, "element_id"):
                    metadata["neo4j_element_id"] = node.element_id
                if hasattr(node, "labels"):
                    metadata["neo4j_labels"] = list(node.labels)
                if hasattr(node, "properties"):
                    metadata["properties"] = dict(node.properties)

                # Create ExtractedEntity
                entity = ExtractedEntity(
                    name=entity_name,
                    entity_type=entity_type,
                    confidence=confidence,
                    context=context,
                    metadata=metadata,
                )

                # Apply confidence threshold
                if entity.confidence >= self.config.confidence_threshold:
                    entities.append(entity)
                    logger.debug(
                        f"Extracted entity: {entity.name} ({entity.entity_type.value}) with confidence {entity.confidence}"
                    )

            except Exception as e:
                logger.warning(f"Failed to convert node to entity: {e}")
                logger.debug(f"Node attributes: {dir(node)}")
                continue

        logger.info(f"Successfully converted {len(entities)} nodes to entities")
        return entities

    async def _perform_custom_prompt_extraction(
        self,
        text: str,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        domain: Optional[PromptDomain] = None,
        custom_prompt: str = "",
    ) -> ExtractionResult:
        """Perform entity extraction using custom prompts.

        Args:
            text: Text to extract entities from
            source_description: Optional description of the text source
            reference_time: Optional reference time for the extraction
            domain: Domain for prompt selection
            custom_prompt: Additional custom instructions for extraction

        Returns:
            ExtractionResult containing extracted entities
        """
        # Set default domain
        extraction_domain = domain or PromptDomain.SOFTWARE_DEVELOPMENT

        # Generate custom prompt messages
        messages = self.prompt_manager.generate_entity_extraction_messages(
            content=text,
            entity_types=self.config.enabled_entity_types,
            domain=extraction_domain,
            custom_prompt=custom_prompt,
            extraction_hints=self.prompt_manager.get_extraction_hints_for_domain(
                extraction_domain
            ),
            reference_time=(reference_time or datetime.now(timezone.utc)).isoformat(),
        )

        # Use Graphiti's LLM client directly for extraction
        if not self.graphiti_manager.llm_client:
            raise RuntimeError("LLM client not available in GraphitiManager")

        # Call the LLM with custom prompts
        response = await self.graphiti_manager.llm_client.generate_response(messages)

        # Extract text content from response
        response_text = (
            response.get("content", "") if isinstance(response, dict) else str(response)
        )

        # Parse the response to extract entities
        entities = self._parse_llm_response_to_entities(response_text, text)

        # Create episode for tracking (optional)
        episode_id = None
        try:
            episode_id = await self.graphiti_manager.add_episode(
                name=f"Custom prompt extraction - {datetime.now(timezone.utc).isoformat()}",
                content=text,
                episode_type=EpisodeType.text,
                source_description=source_description
                or "Custom prompt entity extraction",
                reference_time=reference_time or datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(f"Failed to create episode for custom extraction: {e}")

        return ExtractionResult(
            entities=entities,
            source_text=text,
            episode_id=episode_id,
            metadata={
                "source_description": source_description,
                "reference_time": (
                    reference_time.isoformat() if reference_time else None
                ),
                "domain": extraction_domain.value,
                "custom_prompt": custom_prompt,
                "extraction_method": "custom_prompts",
            },
        )

    def _parse_llm_response_to_entities(
        self, response: str, source_text: str
    ) -> List[ExtractedEntity]:
        """Parse LLM response to extract entities.

        Args:
            response: LLM response text
            source_text: Original source text

        Returns:
            List of ExtractedEntity objects
        """
        entities = []

        try:
            # Try to parse as JSON first
            import json

            response_data = json.loads(response)

            if isinstance(response_data, dict) and "entities" in response_data:
                entity_list = response_data["entities"]
            elif isinstance(response_data, list):
                entity_list = response_data
            else:
                logger.warning("Unexpected response format from LLM")
                return entities

            for entity_data in entity_list:
                if isinstance(entity_data, dict):
                    name = entity_data.get("name", "")
                    entity_type_id = entity_data.get("entity_type_id", 0)
                    confidence = entity_data.get("confidence", 0.8)

                    # Map entity_type_id to EntityType
                    if entity_type_id < len(self.config.enabled_entity_types):
                        entity_type = self.config.enabled_entity_types[entity_type_id]
                    else:
                        entity_type = EntityType.CONCEPT  # Default fallback

                    # Apply confidence threshold
                    if confidence >= self.config.confidence_threshold and name:
                        entity = ExtractedEntity(
                            name=name,
                            entity_type=entity_type,
                            confidence=confidence,
                            context=entity_data.get("context", ""),
                            metadata={
                                "extraction_method": "custom_prompts",
                                "entity_type_id": entity_type_id,
                            },
                        )
                        entities.append(entity)

        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract entities from text
            logger.warning(
                "Failed to parse LLM response as JSON, attempting text parsing"
            )
            entities = self._extract_entities_from_text_response(response, source_text)

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")

        return entities

    def _extract_entities_from_text_response(
        self, response: str, source_text: str
    ) -> List[ExtractedEntity]:
        """Extract entities from text-based LLM response.

        Args:
            response: LLM response text
            source_text: Original source text

        Returns:
            List of ExtractedEntity objects
        """
        entities = []

        # Simple text parsing - look for entity patterns
        # This is a fallback method when JSON parsing fails
        lines = response.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for patterns like "Entity: Name (Type)"
            import re

            pattern = r"(?:Entity|Name):\s*([^(]+)\s*\(([^)]+)\)"
            match = re.search(pattern, line, re.IGNORECASE)

            if match:
                name = match.group(1).strip()
                type_str = match.group(2).strip().upper()

                # Try to map to EntityType
                try:
                    entity_type = EntityType(type_str)
                except ValueError:
                    entity_type = EntityType.CONCEPT

                if entity_type in self.config.enabled_entity_types:
                    entity = ExtractedEntity(
                        name=name,
                        entity_type=entity_type,
                        confidence=0.7,  # Default confidence for text parsing
                        context="",
                        metadata={
                            "extraction_method": "text_parsing_fallback",
                        },
                    )
                    entities.append(entity)

        return entities

    def _generate_cache_key(
        self, text: str, source_description: Optional[str] = None
    ) -> str:
        """Generate a cache key for the given text and source description.

        Args:
            text: Text content
            source_description: Optional source description

        Returns:
            Cache key string
        """
        content = f"{text}|{source_description or ''}"
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[ExtractionResult]:
        """Get extraction result from cache if not expired.

        Args:
            cache_key: Cache key

        Returns:
            Cached ExtractionResult or None if not found/expired
        """
        if cache_key not in self._cache:
            return None

        # Check if cache entry is expired
        timestamp = self._cache_timestamps.get(cache_key, 0)
        if time.time() - timestamp > self.config.cache_ttl:
            # Remove expired entry
            del self._cache[cache_key]
            del self._cache_timestamps[cache_key]
            return None

        return self._cache[cache_key]

    def _store_in_cache(self, cache_key: str, result: ExtractionResult) -> None:
        """Store extraction result in cache.

        Args:
            cache_key: Cache key
            result: ExtractionResult to cache
        """
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

        # Simple cache size management (keep last 1000 entries)
        if len(self._cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self._cache_timestamps.keys(), key=lambda k: self._cache_timestamps[k]
            )[
                :100
            ]  # Remove 100 oldest entries

            for key in oldest_keys:
                del self._cache[key]
                del self._cache_timestamps[key]

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Entity extraction cache cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics.

        Returns:
            Dictionary containing extraction statistics
        """
        cache_hit_rate = (
            self._stats["cache_hits"]
            / (self._stats["cache_hits"] + self._stats["cache_misses"])
            if (self._stats["cache_hits"] + self._stats["cache_misses"]) > 0
            else 0.0
        )

        return {
            **self._stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._cache),
            "config": {
                "batch_size": self.config.batch_size,
                "max_retries": self.config.max_retries,
                "cache_ttl": self.config.cache_ttl,
                "confidence_threshold": self.config.confidence_threshold,
                "enabled_entity_types": [
                    et.value for et in self.config.enabled_entity_types
                ],
            },
        }

    def reset_statistics(self) -> None:
        """Reset extraction statistics."""
        self._stats = {
            "total_extractions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failed_extractions": 0,
            "total_entities_extracted": 0,
            "concurrent_extractions": 0,
            "queue_size": 0,
            "background_tasks_processed": 0,
        }
        logger.info("Entity extraction statistics reset")

    async def test_integration(self, test_text: Optional[str] = None) -> Dict[str, Any]:
        """Test the Graphiti integration and async processing capabilities with a sample text.

        Args:
            test_text: Optional test text to use for extraction

        Returns:
            Dictionary containing test results and statistics
        """
        if test_text is None:
            test_text = """
            Our microservice architecture includes a user authentication service 
            that connects to a PostgreSQL database. The API endpoints are documented 
            in our Confluence wiki, and the development team led by John Smith 
            maintains this critical component.
            """

        logger.info(
            "Starting comprehensive Graphiti and async processing integration test"
        )

        test_results = {
            "basic_extraction": {},
            "batch_processing": {},
            "async_queue_processing": {},
            "streaming_processing": {},
            "performance_metrics": {},
            "queue_status": {},
            "errors": [],
        }

        start_time = time.time()

        try:
            # Test 1: Basic extraction
            logger.info("Testing basic entity extraction...")
            basic_result = await self.extract_entities(test_text)
            test_results["basic_extraction"] = {
                "entities_found": len(basic_result.entities),
                "processing_time": basic_result.processing_time,
                "episode_id": basic_result.episode_id,
                "errors": basic_result.errors,
                "entity_types": [e.entity_type.value for e in basic_result.entities],
                "entity_names": [e.name for e in basic_result.entities],
            }

            # Test 2: Batch processing
            logger.info("Testing enhanced batch processing...")
            test_texts = [
                test_text,
                test_text + " Additional context.",
                test_text + " More data.",
            ]
            batch_results = await self.extract_entities_batch(test_texts)
            test_results["batch_processing"] = {
                "total_texts": len(test_texts),
                "results_count": len(batch_results),
                "total_entities": sum(len(r.entities) for r in batch_results),
                "average_processing_time": sum(r.processing_time for r in batch_results)
                / len(batch_results),
                "errors": [r.errors for r in batch_results if r.errors],
            }

            # Test 3: Async queue processing
            logger.info("Testing async queue processing...")
            queue_texts = [f"{test_text} Queue test {i}" for i in range(5)]

            # Add progress callback for testing
            progress_updates = []

            def progress_callback(progress: ProcessingProgress):
                progress_updates.append(
                    {
                        "completion_percentage": progress.completion_percentage,
                        "completed_tasks": progress.completed_tasks,
                        "total_tasks": progress.total_tasks,
                        "elapsed_time": progress.elapsed_time,
                    }
                )

            self.add_progress_callback(progress_callback)

            queue_results = await self.extract_entities_async_queue(
                queue_texts, priority=1, wait_for_completion=True
            )

            self.remove_progress_callback(progress_callback)

            test_results["async_queue_processing"] = {
                "total_texts": len(queue_texts),
                "results_count": len(queue_results),
                "total_entities": sum(len(r.entities) for r in queue_results),
                "progress_updates_count": len(progress_updates),
                "final_progress": progress_updates[-1] if progress_updates else None,
                "errors": [r.errors for r in queue_results if r.errors],
            }

            # Test 4: Streaming processing (simulate with async generator)
            logger.info("Testing streaming processing...")

            async def text_generator():
                for i in range(3):
                    yield f"{test_text} Stream item {i}"

            streaming_results = []
            async for result in self.extract_entities_streaming(
                text_generator(), chunk_size=2
            ):
                streaming_results.append(result)

            test_results["streaming_processing"] = {
                "results_count": len(streaming_results),
                "total_entities": sum(len(r.entities) for r in streaming_results),
                "errors": [r.errors for r in streaming_results if r.errors],
            }

            # Test 5: Queue status and performance metrics
            test_results["queue_status"] = self.get_queue_status()
            test_results["performance_metrics"] = {
                "total_test_time": time.time() - start_time,
                "extraction_statistics": self.get_statistics(),
            }

            logger.info("All integration tests completed successfully")

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            test_results["errors"].append(str(e))

        return test_results

    async def extract_entities_async_queue(
        self,
        texts: List[str],
        source_descriptions: Optional[List[str]] = None,
        reference_times: Optional[List[datetime]] = None,
        priority: int = 0,
        wait_for_completion: bool = True,
    ) -> List[ExtractionResult]:
        """Extract entities using the async queue system for better throughput.

        Args:
            texts: List of texts to extract entities from
            source_descriptions: Optional list of source descriptions
            reference_times: Optional list of reference times
            priority: Priority level for these tasks (higher = more priority)
            wait_for_completion: Whether to wait for all tasks to complete

        Returns:
            List of ExtractionResult objects
        """
        if not texts:
            return []

        logger.info(f"Queuing {len(texts)} texts for async extraction")

        # Prepare task data
        tasks = []
        futures = []

        for i, text in enumerate(texts):
            task_id = f"async_extract_{int(time.time() * 1000)}_{i}"

            task = ExtractionTask(
                task_id=task_id,
                text=text,
                source_description=(
                    source_descriptions[i] if source_descriptions else None
                ),
                reference_time=reference_times[i] if reference_times else None,
                priority=priority,
            )

            # Create future for result if waiting
            if wait_for_completion:
                future = asyncio.Future()
                self._result_futures[task_id] = future
                futures.append(future)

            tasks.append(task)

        # Update progress tracking
        self._current_progress.total_tasks += len(tasks)

        # Queue all tasks (sorted by priority)
        tasks.sort(key=lambda t: t.priority, reverse=True)
        for task in tasks:
            await self._task_queue.put(task)

        self._stats["queue_size"] = self._task_queue.qsize()

        if wait_for_completion:
            # Wait for all results
            logger.debug(
                f"Waiting for {len(futures)} async extraction tasks to complete"
            )
            results = await asyncio.gather(*futures, return_exceptions=True)

            # Handle exceptions
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Async extraction failed for text {i}: {result}")
                    error_result = ExtractionResult(
                        source_text=texts[i],
                        errors=[f"Async extraction failed: {str(result)}"],
                    )
                    final_results.append(error_result)
                else:
                    final_results.append(result)

            return final_results
        else:
            logger.info(f"Queued {len(tasks)} tasks for background processing")
            return []

    async def extract_entities_streaming(
        self,
        texts: AsyncGenerator[str, None],
        chunk_size: int = 10,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> AsyncGenerator[ExtractionResult, None]:
        """Stream entity extraction for large datasets.

        Args:
            texts: Async generator yielding texts to process
            chunk_size: Number of texts to process in each chunk
            progress_callback: Optional callback for progress updates

        Yields:
            ExtractionResult objects as they are completed
        """
        logger.info("Starting streaming entity extraction")

        if progress_callback:
            self.add_progress_callback(progress_callback)

        chunk = []
        total_processed = 0

        try:
            async for text in texts:
                chunk.append(text)

                if len(chunk) >= chunk_size:
                    # Process chunk
                    results = await self.extract_entities_batch(chunk)

                    for result in results:
                        yield result
                        total_processed += 1

                    chunk = []
                    logger.debug(f"Streaming: processed {total_processed} texts so far")

            # Process remaining texts in final chunk
            if chunk:
                results = await self.extract_entities_batch(chunk)
                for result in results:
                    yield result
                    total_processed += 1

        finally:
            if progress_callback:
                self.remove_progress_callback(progress_callback)

            logger.info(
                f"Streaming extraction completed: {total_processed} texts processed"
            )

    def add_progress_callback(
        self, callback: Callable[[ProcessingProgress], None]
    ) -> None:
        """Add a progress callback function.

        Args:
            callback: Function to call with progress updates
        """
        self._progress_callbacks.append(callback)

        # Start progress reporting if not already running
        if self._progress_task is None or self._progress_task.done():
            self._progress_task = asyncio.create_task(self._progress_reporter())

    def remove_progress_callback(
        self, callback: Callable[[ProcessingProgress], None]
    ) -> None:
        """Remove a progress callback function.

        Args:
            callback: Function to remove from progress updates
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    async def _progress_reporter(self) -> None:
        """Background task for reporting progress to registered callbacks."""
        while self._progress_callbacks:
            try:
                # Update queue size stat
                self._stats["queue_size"] = self._task_queue.qsize()

                # Call all registered callbacks
                for callback in self._progress_callbacks[
                    :
                ]:  # Copy to avoid modification during iteration
                    try:
                        callback(self._current_progress)
                    except Exception as e:
                        logger.error(f"Progress callback failed: {e}")
                        # Remove failed callback
                        if callback in self._progress_callbacks:
                            self._progress_callbacks.remove(callback)

                await asyncio.sleep(self.config.progress_callback_interval)

            except Exception as e:
                logger.error(f"Progress reporter error: {e}")
                await asyncio.sleep(1.0)

        logger.debug("Progress reporter stopped - no more callbacks")

    async def wait_for_queue_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all queued tasks to complete.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            True if all tasks completed, False if timeout occurred
        """
        try:
            await asyncio.wait_for(self._task_queue.join(), timeout=timeout)
            logger.info("All queued extraction tasks completed")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Queue completion timed out after {timeout}s")
            return False

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue and processing status.

        Returns:
            Dictionary with queue status information
        """
        return {
            "queue_size": self._task_queue.qsize(),
            "max_queue_size": self._task_queue.maxsize,
            "active_workers": len(
                [w for w in self._background_workers if not w.done()]
            ),
            "total_workers": len(self._background_workers),
            "concurrent_extractions": self._stats["concurrent_extractions"],
            "max_concurrent": self.config.max_concurrent_extractions,
            "progress": {
                "total_tasks": self._current_progress.total_tasks,
                "completed_tasks": self._current_progress.completed_tasks,
                "failed_tasks": self._current_progress.failed_tasks,
                "in_progress_tasks": self._current_progress.in_progress_tasks,
                "completion_percentage": self._current_progress.completion_percentage,
                "elapsed_time": self._current_progress.elapsed_time,
            },
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown the entity extractor and cleanup resources."""
        logger.info("Shutting down EntityExtractor...")

        # Signal workers to stop
        self._worker_shutdown_event.set()

        # Cancel progress reporter
        if self._progress_task and not self._progress_task.done():
            self._progress_task.cancel()
            try:
                await self._progress_task
            except asyncio.CancelledError:
                pass

        # Wait for background workers to finish
        if self._background_workers:
            logger.debug("Waiting for background workers to shutdown...")
            await asyncio.gather(*self._background_workers, return_exceptions=True)

        # Cancel any remaining active tasks
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()

        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)

        # Clear futures and queues
        for future in self._result_futures.values():
            if not future.done():
                future.cancel()
        self._result_futures.clear()

        # Clear queue
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
                self._task_queue.task_done()
            except asyncio.QueueEmpty:
                break

        logger.info("EntityExtractor shutdown complete")

    def __del__(self):
        """Cleanup when object is destroyed."""
        # Schedule cleanup if event loop is running
        try:
            loop = asyncio.get_running_loop()
            if not loop.is_closed():
                loop.create_task(self.shutdown())
        except RuntimeError:
            # No event loop running, cleanup synchronously
            self._thread_pool.shutdown(wait=False)
