"""
Topic-Driven Search Chaining for Search Enhancement.

This module implements intelligent topic-based search progression that creates
discovery chains from initial queries to related content exploration.
"""

import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from ...utils.logging import LoggingConfig
from ..models import SearchResult
from ..nlp.spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer
from .knowledge_graph import DocumentKnowledgeGraph

logger = LoggingConfig.get_logger(__name__)


class ChainStrategy(Enum):
    """Strategies for generating topic search chains."""

    BREADTH_FIRST = "breadth_first"  # Explore broad related topics first
    DEPTH_FIRST = "depth_first"  # Deep dive into specific topic areas
    RELEVANCE_RANKED = (
        "relevance_ranked"  # Order by semantic relevance to original query
    )
    MIXED_EXPLORATION = "mixed_exploration"  # Balance breadth and depth


@dataclass
class TopicChainLink:
    """Individual link in a topic search chain."""

    query: str  # Generated search query
    topic_focus: str  # Primary topic this query explores
    related_topics: list[str]  # Secondary topics covered
    chain_position: int  # Position in the chain (0 = original)
    relevance_score: float  # Relevance to original query (0-1)

    # Chain context
    parent_query: str | None = None  # Query that led to this one
    exploration_type: str = "related"  # "related", "deeper", "broader", "alternative"
    reasoning: str = ""  # Why this query was generated

    # Semantic context from spaCy
    semantic_keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)


@dataclass
class TopicSearchChain:
    """Complete topic search chain with metadata."""

    original_query: str
    chain_links: list[TopicChainLink]
    strategy: ChainStrategy

    # Chain characteristics
    total_topics_covered: int = 0
    estimated_discovery_potential: float = 0.0  # 0-1 score
    chain_coherence_score: float = 0.0  # How well-connected the chain is

    # Generation metadata
    generation_time_ms: float = 0.0
    spacy_analysis: QueryAnalysis | None = None


class TopicRelationshipMap:
    """Maps relationships between topics using spaCy similarity and co-occurrence."""

    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the topic relationship mapper."""
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)

        # Topic relationship storage
        self.topic_similarity_cache: dict[tuple[str, str], float] = {}
        self.topic_cooccurrence: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.topic_document_frequency: dict[str, int] = defaultdict(int)
        self.topic_entities_map: dict[str, set[str]] = defaultdict(set)

        # Relationship strength thresholds
        self.similarity_threshold = 0.4
        self.cooccurrence_threshold = 2

    def build_topic_map(self, search_results: list[SearchResult]) -> None:
        """Build topic relationship map from search results."""
        logger.info(
            f"Building topic relationship map from {len(search_results)} search results"
        )
        start_time = time.time()

        # Extract all topics and their co-occurrence patterns
        for result in search_results:
            topics = self._extract_topics_from_result(result)
            entities = self._extract_entities_from_result(result)

            # Count document frequency for each topic
            for topic in topics:
                self.topic_document_frequency[topic] += 1
                # Map topics to entities they appear with
                self.topic_entities_map[topic].update(entities)

            # Record co-occurrence patterns
            for i, topic1 in enumerate(topics):
                for j, topic2 in enumerate(topics):
                    if i != j:
                        self.topic_cooccurrence[topic1][topic2] += 1

        build_time = (time.time() - start_time) * 1000
        logger.info(
            f"Topic relationship map built in {build_time:.2f}ms",
            unique_topics=len(self.topic_document_frequency),
            total_cooccurrences=sum(
                len(cooc) for cooc in self.topic_cooccurrence.values()
            ),
        )

    def find_related_topics(
        self,
        source_topic: str,
        max_related: int = 5,
        include_semantic: bool = True,
        include_cooccurrence: bool = True,
    ) -> list[tuple[str, float, str]]:
        """Find topics related to the source topic.

        Returns:
            List of (topic, score, relationship_type) tuples
        """
        related_topics = []

        if include_semantic:
            # Find semantically similar topics using spaCy
            semantic_related = self._find_semantic_related_topics(
                source_topic, max_related
            )
            for topic, score in semantic_related:
                related_topics.append((topic, score, "semantic_similarity"))

        if include_cooccurrence:
            # Find co-occurring topics
            cooccurrence_related = self._find_cooccurrence_related_topics(
                source_topic, max_related
            )
            for topic, score in cooccurrence_related:
                related_topics.append((topic, score, "cooccurrence"))

        # Combine and deduplicate, keeping highest score per topic
        topic_best_scores = {}
        for topic, score, rel_type in related_topics:
            if topic not in topic_best_scores or score > topic_best_scores[topic][0]:
                topic_best_scores[topic] = (score, rel_type)

        # Sort by score and return top results
        final_related = [
            (topic, score, rel_type)
            for topic, (score, rel_type) in topic_best_scores.items()
        ]
        final_related.sort(key=lambda x: x[1], reverse=True)

        return final_related[:max_related]

    def _extract_topics_from_result(self, result: SearchResult) -> list[str]:
        """Extract topics from a search result."""
        topics = []

        # Extract from topics field
        for topic_item in result.topics:
            if isinstance(topic_item, str):
                topics.append(topic_item.lower().strip())
            elif isinstance(topic_item, dict):
                if "text" in topic_item:
                    topics.append(str(topic_item["text"]).lower().strip())
                elif "topic" in topic_item:
                    topics.append(str(topic_item["topic"]).lower().strip())

        # Extract from breadcrumb hierarchy
        if result.breadcrumb_text:
            breadcrumb_topics = [
                topic.strip().lower()
                for topic in result.breadcrumb_text.split(" > ")
                if topic.strip()
            ]
            topics.extend(breadcrumb_topics)

        # Extract from section information
        if result.section_title:
            topics.append(result.section_title.lower().strip())

        if result.section_type:
            topics.append(result.section_type.lower().strip())

        # Extract from source type
        if result.source_type:
            topics.append(result.source_type.lower().strip())

        return list(set(topics))  # Remove duplicates

    def _extract_entities_from_result(self, result: SearchResult) -> list[str]:
        """Extract entities from a search result."""
        entities = []

        # Extract from entities field
        for entity_item in result.entities:
            if isinstance(entity_item, str):
                entities.append(entity_item.lower().strip())
            elif isinstance(entity_item, dict):
                if "text" in entity_item:
                    entities.append(str(entity_item["text"]).lower().strip())
                elif "entity" in entity_item:
                    entities.append(str(entity_item["entity"]).lower().strip())

        # Extract from titles and names
        if result.source_title:
            entities.append(result.source_title.lower().strip())
        if result.project_name:
            entities.append(result.project_name.lower().strip())

        return list(set(entities))

    def _find_semantic_related_topics(
        self, source_topic: str, max_related: int
    ) -> list[tuple[str, float]]:
        """Find semantically related topics using spaCy similarity."""
        related = []

        source_doc = self.spacy_analyzer.nlp(source_topic)

        for topic in self.topic_document_frequency.keys():
            if topic == source_topic:
                continue

            # Check cache first
            cache_key = (source_topic, topic)
            if cache_key in self.topic_similarity_cache:
                similarity = self.topic_similarity_cache[cache_key]
            else:
                # Calculate similarity using spaCy
                topic_doc = self.spacy_analyzer.nlp(topic)
                similarity = source_doc.similarity(topic_doc)
                self.topic_similarity_cache[cache_key] = similarity

            if similarity > self.similarity_threshold:
                # Weight by document frequency (more common topics get slight boost)
                doc_freq_weight = min(
                    1.2, 1.0 + (self.topic_document_frequency[topic] / 100)
                )
                weighted_score = similarity * doc_freq_weight
                related.append((topic, weighted_score))

        related.sort(key=lambda x: x[1], reverse=True)
        return related[:max_related]

    def _find_cooccurrence_related_topics(
        self, source_topic: str, max_related: int
    ) -> list[tuple[str, float]]:
        """Find topics that frequently co-occur with the source topic."""
        related = []

        if source_topic not in self.topic_cooccurrence:
            return related

        source_freq = self.topic_document_frequency[source_topic]

        for topic, cooccur_count in self.topic_cooccurrence[source_topic].items():
            if cooccur_count >= self.cooccurrence_threshold:
                # Calculate co-occurrence strength using PMI-like measure
                topic_freq = self.topic_document_frequency[topic]
                total_docs = max(sum(self.topic_document_frequency.values()), 1)

                # Point-wise Mutual Information (PMI) style calculation
                pmi = math.log2(
                    (cooccur_count * total_docs) / (source_freq * topic_freq + 1)
                )

                # Normalize to 0-1 range
                normalized_score = max(0, min(1, (pmi + 5) / 10))  # Rough normalization
                related.append((topic, normalized_score))

        related.sort(key=lambda x: x[1], reverse=True)
        return related[:max_related]


class TopicSearchChainGenerator:
    """Generates intelligent topic-driven search chains."""

    def __init__(
        self,
        spacy_analyzer: SpaCyQueryAnalyzer,
        knowledge_graph: DocumentKnowledgeGraph | None = None,
    ):
        """Initialize the topic search chain generator."""
        self.spacy_analyzer = spacy_analyzer
        self.knowledge_graph = knowledge_graph
        self.topic_map = TopicRelationshipMap(spacy_analyzer)
        self.logger = LoggingConfig.get_logger(__name__)

        # Chain generation configuration
        self.max_chain_length = 6
        self.min_relevance_threshold = 0.3
        self.diversity_factor = 0.7  # Balance between relevance and diversity

    def initialize_from_results(self, search_results: list[SearchResult]) -> None:
        """Initialize topic relationships from existing search results."""
        self.topic_map.build_topic_map(search_results)
        logger.info("Topic search chain generator initialized with topic relationships")

    def generate_search_chain(
        self,
        original_query: str,
        strategy: ChainStrategy = ChainStrategy.MIXED_EXPLORATION,
        max_links: int = 5,
    ) -> TopicSearchChain:
        """Generate a topic-driven search chain from the original query."""
        start_time = time.time()

        # Analyze original query with spaCy
        spacy_analysis = self.spacy_analyzer.analyze_query_semantic(original_query)

        # Extract primary topics from the query
        primary_topics = self._extract_primary_topics(spacy_analysis, original_query)

        # Generate chain links based on strategy
        if strategy == ChainStrategy.BREADTH_FIRST:
            chain_links = self._generate_breadth_first_chain(
                original_query, primary_topics, spacy_analysis, max_links
            )
        elif strategy == ChainStrategy.DEPTH_FIRST:
            chain_links = self._generate_depth_first_chain(
                original_query, primary_topics, spacy_analysis, max_links
            )
        elif strategy == ChainStrategy.RELEVANCE_RANKED:
            chain_links = self._generate_relevance_ranked_chain(
                original_query, primary_topics, spacy_analysis, max_links
            )
        else:  # MIXED_EXPLORATION
            chain_links = self._generate_mixed_exploration_chain(
                original_query, primary_topics, spacy_analysis, max_links
            )

        # Calculate chain metrics
        total_topics = len(
            {link.topic_focus for link in chain_links}
            | {topic for link in chain_links for topic in link.related_topics}
        )

        discovery_potential = self._calculate_discovery_potential(
            chain_links, spacy_analysis
        )
        coherence_score = self._calculate_chain_coherence(chain_links)

        generation_time = (time.time() - start_time) * 1000

        chain = TopicSearchChain(
            original_query=original_query,
            chain_links=chain_links,
            strategy=strategy,
            total_topics_covered=total_topics,
            estimated_discovery_potential=discovery_potential,
            chain_coherence_score=coherence_score,
            generation_time_ms=generation_time,
            spacy_analysis=spacy_analysis,
        )

        logger.info(
            f"Generated topic search chain in {generation_time:.2f}ms",
            strategy=strategy.value,
            chain_length=len(chain_links),
            topics_covered=total_topics,
            discovery_potential=f"{discovery_potential:.2f}",
            coherence=f"{coherence_score:.2f}",
        )

        return chain

    def _extract_primary_topics(
        self, spacy_analysis: QueryAnalysis, query: str
    ) -> list[str]:
        """Extract primary topics from spaCy analysis."""
        topics = []

        # Use main concepts as primary topics
        topics.extend(spacy_analysis.main_concepts)

        # Use semantic keywords as topics
        topics.extend(spacy_analysis.semantic_keywords[:3])  # Top 3 keywords

        # Use entities as topics
        for entity_text, _entity_label in spacy_analysis.entities:
            topics.append(entity_text.lower())

        return list(set(topics))

    def _generate_breadth_first_chain(
        self,
        original_query: str,
        primary_topics: list[str],
        spacy_analysis: QueryAnalysis,
        max_links: int,
    ) -> list[TopicChainLink]:
        """Generate breadth-first exploration chain."""
        chain_links = []
        explored_topics = set(primary_topics)

        for link_idx in range(max_links):
            if link_idx == 0:
                # First link: explore related topics broadly
                if primary_topics:
                    primary_topic = primary_topics[0]
                    related_topics = self.topic_map.find_related_topics(
                        primary_topic, max_related=3, include_semantic=True
                    )

                    if related_topics:
                        # Create query exploring multiple related topics
                        related_topic_names = [
                            topic for topic, score, rel_type in related_topics[:2]
                        ]
                        query = f"{primary_topic} related to {' and '.join(related_topic_names)}"

                        chain_links.append(
                            TopicChainLink(
                                query=query,
                                topic_focus=primary_topic,
                                related_topics=related_topic_names,
                                chain_position=link_idx,
                                relevance_score=0.9,
                                parent_query=original_query,
                                exploration_type="broader",
                                reasoning=f"Exploring topics related to '{primary_topic}'",
                                semantic_keywords=spacy_analysis.semantic_keywords[:3],
                                entities=[
                                    ent[0] for ent in spacy_analysis.entities[:2]
                                ],
                            )
                        )

                        explored_topics.update(related_topic_names)
            else:
                # Subsequent links: explore new topic areas
                candidate_topics = []
                for explored_topic in list(explored_topics):
                    related = self.topic_map.find_related_topics(
                        explored_topic, max_related=2
                    )
                    for topic, score, _rel_type in related:
                        if topic not in explored_topics:
                            candidate_topics.append((topic, score, explored_topic))

                if candidate_topics:
                    # Pick highest scoring unexplored topic
                    candidate_topics.sort(key=lambda x: x[1], reverse=True)
                    new_topic, score, parent_topic = candidate_topics[0]

                    query = f"explore {new_topic} in context of {parent_topic}"

                    chain_links.append(
                        TopicChainLink(
                            query=query,
                            topic_focus=new_topic,
                            related_topics=[parent_topic],
                            chain_position=link_idx,
                            relevance_score=score * 0.8,  # Decay relevance over chain
                            parent_query=(
                                chain_links[-1].query if chain_links else original_query
                            ),
                            exploration_type="broader",
                            reasoning=f"Broadening exploration to '{new_topic}'",
                            semantic_keywords=[new_topic, parent_topic],
                        )
                    )

                    explored_topics.add(new_topic)

        return chain_links

    def _generate_depth_first_chain(
        self,
        original_query: str,
        primary_topics: list[str],
        spacy_analysis: QueryAnalysis,
        max_links: int,
    ) -> list[TopicChainLink]:
        """Generate depth-first exploration chain."""
        chain_links = []
        current_topic = primary_topics[0] if primary_topics else "general"

        for link_idx in range(max_links):
            if link_idx == 0:
                # First link: deep dive into primary topic
                query = f"detailed information about {current_topic}"

                chain_links.append(
                    TopicChainLink(
                        query=query,
                        topic_focus=current_topic,
                        related_topics=[],
                        chain_position=link_idx,
                        relevance_score=1.0,
                        parent_query=original_query,
                        exploration_type="deeper",
                        reasoning=f"Deep dive into '{current_topic}'",
                        semantic_keywords=spacy_analysis.semantic_keywords[:3],
                    )
                )
            else:
                # Subsequent links: progressively deeper into topic
                related_topics = self.topic_map.find_related_topics(
                    current_topic, max_related=2, include_semantic=True
                )

                if related_topics:
                    # Pick most semantically similar topic for deeper exploration
                    next_topic, score, rel_type = related_topics[0]

                    if rel_type == "semantic_similarity":
                        query = f"advanced {next_topic} concepts and {current_topic} integration"
                    else:
                        query = f"how {next_topic} connects to {current_topic}"

                    chain_links.append(
                        TopicChainLink(
                            query=query,
                            topic_focus=next_topic,
                            related_topics=[current_topic],
                            chain_position=link_idx,
                            relevance_score=score * (0.9**link_idx),  # Decay over depth
                            parent_query=chain_links[-1].query,
                            exploration_type="deeper",
                            reasoning=f"Deeper exploration of '{next_topic}' from '{current_topic}'",
                            semantic_keywords=[next_topic, current_topic],
                        )
                    )

                    current_topic = next_topic
                else:
                    break

        return chain_links

    def _generate_relevance_ranked_chain(
        self,
        original_query: str,
        primary_topics: list[str],
        spacy_analysis: QueryAnalysis,
        max_links: int,
    ) -> list[TopicChainLink]:
        """Generate chain ordered by relevance to original query."""
        chain_links = []

        # Collect all related topics with relevance scores
        all_related_topics = []
        for primary_topic in primary_topics:
            related = self.topic_map.find_related_topics(
                primary_topic,
                max_related=10,
                include_semantic=True,
                include_cooccurrence=True,
            )
            for topic, score, rel_type in related:
                # Calculate relevance to original query using spaCy
                query_doc = self.spacy_analyzer.nlp(original_query)
                topic_doc = self.spacy_analyzer.nlp(topic)
                query_relevance = query_doc.similarity(topic_doc)

                combined_score = (score + query_relevance) / 2
                all_related_topics.append(
                    (topic, combined_score, rel_type, primary_topic)
                )

        # Sort by combined relevance score
        all_related_topics.sort(key=lambda x: x[1], reverse=True)

        # Generate chain links from top-ranked topics
        for link_idx in range(min(max_links, len(all_related_topics))):
            topic, score, rel_type, parent_topic = all_related_topics[link_idx]

            if rel_type == "semantic_similarity":
                query = f"information about {topic} similar to {parent_topic}"
            else:
                query = f"{topic} related content and {parent_topic} connections"

            chain_links.append(
                TopicChainLink(
                    query=query,
                    topic_focus=topic,
                    related_topics=[parent_topic],
                    chain_position=link_idx,
                    relevance_score=score,
                    parent_query=(
                        original_query if link_idx == 0 else chain_links[-1].query
                    ),
                    exploration_type="related",
                    reasoning=f"High relevance to original query ({rel_type})",
                    semantic_keywords=[topic, parent_topic],
                )
            )

        return chain_links

    def _generate_mixed_exploration_chain(
        self,
        original_query: str,
        primary_topics: list[str],
        spacy_analysis: QueryAnalysis,
        max_links: int,
    ) -> list[TopicChainLink]:
        """Generate mixed exploration chain balancing breadth and depth."""
        chain_links = []
        explored_topics = set(primary_topics)

        for link_idx in range(max_links):
            if link_idx == 0:
                # Start with breadth
                breadth_links = self._generate_breadth_first_chain(
                    original_query, primary_topics, spacy_analysis, 1
                )
                if breadth_links:
                    chain_links.extend(breadth_links)
                    for link in breadth_links:
                        explored_topics.update(link.related_topics)
            elif link_idx % 2 == 1:
                # Odd positions: depth exploration
                if chain_links:
                    last_topic = chain_links[-1].topic_focus
                    depth_links = self._generate_depth_first_chain(
                        last_topic, [last_topic], spacy_analysis, 1
                    )
                    if depth_links:
                        depth_link = depth_links[0]
                        depth_link.chain_position = link_idx
                        depth_link.parent_query = chain_links[-1].query
                        chain_links.append(depth_link)
                        explored_topics.add(depth_link.topic_focus)
            else:
                # Even positions: breadth exploration
                relevance_links = self._generate_relevance_ranked_chain(
                    original_query, list(explored_topics), spacy_analysis, 1
                )
                if relevance_links:
                    relevance_link = relevance_links[0]
                    relevance_link.chain_position = link_idx
                    relevance_link.parent_query = (
                        chain_links[-1].query if chain_links else original_query
                    )
                    chain_links.append(relevance_link)
                    explored_topics.add(relevance_link.topic_focus)

        return chain_links

    def _calculate_discovery_potential(
        self, chain_links: list[TopicChainLink], spacy_analysis: QueryAnalysis
    ) -> float:
        """Calculate the discovery potential of the chain."""
        if not chain_links:
            return 0.0

        # Factors contributing to discovery potential:
        # 1. Topic diversity
        unique_topics = {link.topic_focus for link in chain_links}
        topic_diversity = len(unique_topics) / len(chain_links) if chain_links else 0

        # 2. Average relevance score
        avg_relevance = sum(link.relevance_score for link in chain_links) / len(
            chain_links
        )

        # 3. Exploration type diversity
        exploration_types = {link.exploration_type for link in chain_links}
        type_diversity = len(exploration_types) / 4  # Max 4 types

        # 4. Chain length factor (longer chains = more discovery)
        length_factor = min(1.0, len(chain_links) / 5)

        # Weighted combination
        discovery_potential = (
            topic_diversity * 0.3
            + avg_relevance * 0.4
            + type_diversity * 0.2
            + length_factor * 0.1
        )

        return min(1.0, discovery_potential)

    def _calculate_chain_coherence(self, chain_links: list[TopicChainLink]) -> float:
        """Calculate how coherent/connected the chain is."""
        if len(chain_links) < 2:
            return 1.0

        coherence_scores = []

        for i in range(1, len(chain_links)):
            prev_link = chain_links[i - 1]
            curr_link = chain_links[i]

            # Check topic overlap between consecutive links
            prev_topics = set([prev_link.topic_focus] + prev_link.related_topics)
            curr_topics = set([curr_link.topic_focus] + curr_link.related_topics)

            overlap = len(prev_topics.intersection(curr_topics))
            union = len(prev_topics.union(curr_topics))

            link_coherence = overlap / max(union, 1)
            coherence_scores.append(link_coherence)

        return sum(coherence_scores) / len(coherence_scores)
