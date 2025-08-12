"""Unit tests for cross-document intelligence edge cases and error handling."""

from unittest.mock import AsyncMock, Mock

import pytest
from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
    CitationNetworkAnalyzer,
    ConflictDetector,
    DocumentClusterAnalyzer,
    DocumentSimilarityCalculator,
    RelationshipType,
)


class TestDocumentSimilarityCalculatorEdgeCases:
    """Test edge cases for DocumentSimilarityCalculator."""

    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Create a mock SpaCy analyzer."""
        analyzer = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.5
        analyzer.nlp.return_value = mock_doc
        return analyzer

    @pytest.fixture
    def similarity_calculator(self, mock_spacy_analyzer):
        """Create a DocumentSimilarityCalculator instance."""
        return DocumentSimilarityCalculator(mock_spacy_analyzer)

    def test_calculate_similarity_with_none_entities(self, similarity_calculator):
        """Test similarity calculation when documents have None entities."""
        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Test document",
            source_type="confluence",
            source_title="Doc 1",
            entities=None,
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another document",
            source_type="confluence",
            source_title="Doc 2",
            entities=None,
        )

        similarity = similarity_calculator.calculate_similarity(doc1, doc2)

        assert similarity.similarity_score >= 0
        assert similarity.shared_entities == []

    def test_calculate_similarity_with_none_topics(self, similarity_calculator):
        """Test similarity calculation when documents have None topics."""
        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Test document",
            source_type="confluence",
            source_title="Doc 1",
            topics=None,
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another document",
            source_type="confluence",
            source_title="Doc 2",
            topics=None,
        )

        similarity = similarity_calculator.calculate_similarity(doc1, doc2)

        assert similarity.similarity_score >= 0
        assert similarity.shared_topics == []

    def test_calculate_similarity_with_empty_text(self, similarity_calculator):
        """Test similarity calculation with empty text."""
        doc1 = create_hybrid_search_result(
            score=0.8, text="", source_type="confluence", source_title="Doc 1"
        )
        doc2 = create_hybrid_search_result(
            score=0.8, text="", source_type="confluence", source_title="Doc 2"
        )

        similarity = similarity_calculator.calculate_similarity(doc1, doc2)

        assert similarity.similarity_score >= 0

    def test_calculate_similarity_spacy_error_handling(self, similarity_calculator):
        """Test error handling when spaCy raises an exception."""
        similarity_calculator.spacy_analyzer.nlp.side_effect = Exception("SpaCy error")

        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Test document",
            source_type="confluence",
            source_title="Doc 1",
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Another document",
            source_type="confluence",
            source_title="Doc 2",
        )

        similarity = similarity_calculator.calculate_similarity(doc1, doc2)

        # Should handle error gracefully
        assert similarity.similarity_score >= 0

    def test_extract_entity_texts_with_mixed_formats(self, similarity_calculator):
        """Test entity text extraction with mixed formats."""
        entities = [
            {"text": "OAuth", "label": "TECH"},  # Dict format
            "JWT",  # String format
            {"text": "", "label": "EMPTY"},  # Empty text
            {"label": "NO_TEXT"},  # Missing text key
            None,  # None value
            "",  # Empty string
        ]

        extracted = similarity_calculator._extract_entity_texts(entities)

        assert "oauth" in extracted
        assert "jwt" in extracted
        assert len(extracted) == 2  # Only valid entities

    def test_extract_topic_texts_with_mixed_formats(self, similarity_calculator):
        """Test topic text extraction with mixed formats."""
        topics = [
            {"text": "Authentication", "score": 0.9},  # Dict format
            "Security",  # String format
            {"text": "", "score": 0.5},  # Empty text
            {"score": 0.8},  # Missing text key
            None,  # None value
            "",  # Empty string
        ]

        extracted = similarity_calculator._extract_topic_texts(topics)

        assert "authentication" in extracted
        assert "security" in extracted
        assert len(extracted) == 2  # Only valid topics

    def test_calculate_entity_overlap_empty_entities(self, similarity_calculator):
        """Test entity overlap calculation with empty entities."""
        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="confluence",
            source_title="Doc 1",
            entities=[],
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="confluence",
            source_title="Doc 2",
            entities=[],
        )

        overlap = similarity_calculator._calculate_entity_overlap(doc1, doc2)

        assert overlap == 0.0

    def test_calculate_metadata_similarity_missing_project_id(
        self, similarity_calculator
    ):
        """Test metadata similarity when project_id is missing."""
        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="confluence",
            source_title="Doc 1",
            project_id=None,
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="git",
            source_title="Doc 2",
            project_id="project1",
        )

        similarity = similarity_calculator._calculate_metadata_similarity(doc1, doc2)

        assert 0.0 <= similarity <= 1.0

    def test_combine_metric_scores_empty_scores(self, similarity_calculator):
        """Test combining metric scores when scores dict is empty."""
        combined = similarity_calculator._combine_metric_scores({})

        assert combined == 0.0

    def test_combine_metric_scores_unknown_metric(self, similarity_calculator):
        """Test combining metric scores with unknown metric type."""
        unknown_metric = Mock()
        unknown_metric.value = "unknown_metric"

        scores = {unknown_metric: 0.8}

        combined = similarity_calculator._combine_metric_scores(scores)

        assert combined > 0  # Should use default weight

    def test_determine_relationship_type_edge_cases(self, similarity_calculator):
        """Test relationship type determination with edge cases."""
        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="confluence",
            source_title="Doc 1",
            project_id=None,
            cross_references=None,
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="confluence",
            source_title="Doc 2",
            project_id=None,
            cross_references=None,
        )

        rel_type = similarity_calculator._determine_relationship_type(doc1, doc2, {})

        assert rel_type == RelationshipType.SEMANTIC_SIMILARITY


class TestDocumentClusterAnalyzerEdgeCases:
    """Test edge cases for DocumentClusterAnalyzer."""

    @pytest.fixture
    def mock_similarity_calculator(self):
        """Create a mock similarity calculator."""
        calc = Mock()
        mock_similarity = Mock()
        mock_similarity.similarity_score = 0.8
        mock_similarity.shared_entities = ["test"]
        mock_similarity.shared_topics = ["topic"]
        calc.calculate_similarity.return_value = mock_similarity

        # Make the extract methods behave more realistically
        def extract_entity_texts(entities):
            if entities is None or entities == []:
                return []
            # For non-empty entities, extract text
            texts = []
            for entity in entities:
                if isinstance(entity, dict):
                    texts.append(entity.get("text", "").lower())
                elif isinstance(entity, str):
                    texts.append(entity.lower())
            return [t for t in texts if t]

        def extract_topic_texts(topics):
            if topics is None or topics == []:
                return []
            # For non-empty topics, extract text
            texts = []
            for topic in topics:
                if isinstance(topic, dict):
                    texts.append(topic.get("text", "").lower())
                elif isinstance(topic, str):
                    texts.append(topic.lower())
            return [t for t in texts if t]

        calc._extract_entity_texts.side_effect = extract_entity_texts
        calc._extract_topic_texts.side_effect = extract_topic_texts
        return calc

    @pytest.fixture
    def cluster_analyzer(self, mock_similarity_calculator):
        """Create a DocumentClusterAnalyzer instance."""
        return DocumentClusterAnalyzer(mock_similarity_calculator)

    def test_create_clusters_empty_documents(self, cluster_analyzer):
        """Test clustering with empty document list."""
        clusters = cluster_analyzer.create_clusters([])

        assert clusters == []

    def test_create_clusters_single_document(self, cluster_analyzer):
        """Test clustering with single document."""
        doc = create_hybrid_search_result(
            score=0.8,
            text="Test document",
            source_type="confluence",
            source_title="Single Doc",
        )

        clusters = cluster_analyzer.create_clusters([doc], min_cluster_size=1)

        # Should handle single document gracefully: either 0 clusters
        # or exactly 1 cluster that contains the single document id
        assert len(clusters) in (0, 1)
        if len(clusters) == 1:
            assert isinstance(clusters[0].documents, list)
            assert len(clusters[0].documents) == 1
            assert clusters[0].documents[0] == "confluence:Single Doc"

    def test_create_clusters_insufficient_documents_for_min_size(
        self, cluster_analyzer
    ):
        """Test clustering when documents don't meet min_cluster_size."""
        docs = [
            create_hybrid_search_result(
                score=0.8,
                text="Test document 1",
                source_type="confluence",
                source_title="Doc 1",
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Test document 2",
                source_type="confluence",
                source_title="Doc 2",
            ),
        ]

        clusters = cluster_analyzer.create_clusters(docs, min_cluster_size=5)

        assert len(clusters) == 0

    def test_cluster_by_entities_no_entities(self, cluster_analyzer):
        """Test entity-based clustering when documents have no entities."""
        docs = [
            create_hybrid_search_result(
                score=0.8,
                text="Test 1",
                source_type="confluence",
                source_title="Doc 1",
                entities=[],
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Test 2",
                source_type="confluence",
                source_title="Doc 2",
                entities=[],
            ),
        ]

        clusters = cluster_analyzer._cluster_by_entities(
            docs, max_clusters=5, min_cluster_size=2
        )

        assert len(clusters) == 0  # No entities to cluster by

    def test_cluster_by_topics_no_topics(self, cluster_analyzer):
        """Test topic-based clustering when documents have no topics."""
        docs = [
            create_hybrid_search_result(
                score=0.8,
                text="Test 1",
                source_type="confluence",
                source_title="Doc 1",
                topics=[],
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Test 2",
                source_type="confluence",
                source_title="Doc 2",
                topics=[],
            ),
        ]

        clusters = cluster_analyzer._cluster_by_topics(
            docs, max_clusters=5, min_cluster_size=2
        )

        assert len(clusters) == 0  # No topics to cluster by

    def test_cluster_by_projects_no_project_ids(self, cluster_analyzer):
        """Test project-based clustering when documents have no project IDs."""
        docs = [
            create_hybrid_search_result(
                score=0.8,
                text="Test 1",
                source_type="confluence",
                source_title="Doc 1",
                project_id=None,
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Test 2",
                source_type="confluence",
                source_title="Doc 2",
                project_id="",
            ),
        ]

        clusters = cluster_analyzer._cluster_by_projects(
            docs, max_clusters=5, min_cluster_size=2
        )

        assert len(clusters) == 0  # No project IDs to cluster by

    def test_generate_intelligent_cluster_name_edge_cases(self, cluster_analyzer):
        """Test intelligent cluster name generation with edge cases."""
        # Empty entities and topics
        name1 = cluster_analyzer._generate_intelligent_cluster_name([], [], "entity", 1)
        assert "Entity Cluster 1" in name1

        # Single entity/topic
        name2 = cluster_analyzer._generate_intelligent_cluster_name(
            ["oauth"], ["auth"], "mixed", 2
        )
        assert "oauth" in name2.lower() or "auth" in name2.lower()

        # Very long entity names
        long_entities = ["very_long_entity_name_that_exceeds_normal_length"] * 5
        name3 = cluster_analyzer._generate_intelligent_cluster_name(
            long_entities, [], "entity", 3
        )
        assert isinstance(name3, str)
        assert len(name3) > 0

    def test_clean_topic_name_edge_cases(self, cluster_analyzer):
        """Test topic name cleaning with edge cases."""
        assert cluster_analyzer._clean_topic_name("") == ""
        assert cluster_analyzer._clean_topic_name("  oauth  ") == "Oauth"
        assert cluster_analyzer._clean_topic_name("OAUTH") == "OAUTH"
        assert cluster_analyzer._clean_topic_name("oauth_2.0") == "Oauth_2.0"

    def test_calculate_cluster_coherence_single_document(self, cluster_analyzer):
        """Test coherence calculation with single document cluster."""
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentCluster,
        )

        cluster = DocumentCluster(cluster_id="test", name="Test", documents=["doc1"])

        doc = create_hybrid_search_result(
            score=0.8, text="Test", source_type="confluence", source_title="Doc 1"
        )

        coherence = cluster_analyzer._calculate_cluster_coherence(cluster, [doc])

        assert coherence == 1.0  # Single document clusters are perfectly coherent

    def test_calculate_cluster_coherence_no_matching_documents(self, cluster_analyzer):
        """Test coherence calculation when cluster docs don't match provided docs."""
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            DocumentCluster,
        )

        cluster = DocumentCluster(
            cluster_id="test", name="Test", documents=["nonexistent_doc"]
        )

        doc = create_hybrid_search_result(
            score=0.8,
            text="Test",
            source_type="confluence",
            source_title="Different Doc",
        )

        coherence = cluster_analyzer._calculate_cluster_coherence(cluster, [doc])

        assert coherence == 0.0


class TestCitationNetworkAnalyzerEdgeCases:
    """Test edge cases for CitationNetworkAnalyzer."""

    @pytest.fixture
    def citation_analyzer(self):
        """Create a CitationNetworkAnalyzer instance."""
        return CitationNetworkAnalyzer()

    def test_build_citation_network_empty_documents(self, citation_analyzer):
        """Test building citation network with empty document list."""
        network = citation_analyzer.build_citation_network([])

        assert len(network.nodes) == 0
        assert len(network.edges) == 0

    def test_build_citation_network_no_references(self, citation_analyzer):
        """Test building citation network with documents having no references."""
        docs = [
            create_hybrid_search_result(
                score=0.8,
                text="Test 1",
                source_type="confluence",
                source_title="Doc 1",
                cross_references=None,
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Test 2",
                source_type="confluence",
                source_title="Doc 2",
                cross_references=[],
            ),
        ]

        network = citation_analyzer.build_citation_network(docs)

        assert len(network.nodes) == 2
        assert len(network.edges) == 0  # No references = no edges

    def test_find_referenced_document_no_matches(self, citation_analyzer):
        """Test finding referenced document when no matches exist."""
        doc_lookup = {
            "confluence:Doc 1": create_hybrid_search_result(
                score=0.8, text="Test", source_type="confluence", source_title="Doc 1"
            )
        }

        found = citation_analyzer._find_referenced_document(
            "https://nonexistent.com/doc", doc_lookup
        )

        assert found is None

    def test_find_sibling_document_no_matches(self, citation_analyzer):
        """Test finding sibling document when no matches exist."""
        doc_lookup = {
            "confluence:Doc 1": create_hybrid_search_result(
                score=0.8, text="Test", source_type="confluence", source_title="Doc 1"
            )
        }

        found = citation_analyzer._find_sibling_document("Nonexistent Doc", doc_lookup)

        assert found is None

    def test_get_most_authoritative_documents_empty_network(self, citation_analyzer):
        """Test getting authoritative documents from empty network."""
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            CitationNetwork,
        )

        network = CitationNetwork()

        authoritative = citation_analyzer.get_most_authoritative_documents(
            network, limit=5
        )

        assert authoritative == []

    def test_get_most_connected_documents_empty_network(self, citation_analyzer):
        """Test getting connected documents from empty network."""
        from qdrant_loader_mcp_server.search.enhanced.cross_document_intelligence import (
            CitationNetwork,
        )

        network = CitationNetwork()

        connected = citation_analyzer.get_most_connected_documents(network, limit=5)

        assert connected == []


class TestConflictDetectorEdgeCases:
    """Test edge cases for ConflictDetector."""

    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Create a mock SpaCy analyzer."""
        analyzer = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.5
        mock_doc.ents = []
        analyzer.nlp.return_value = mock_doc
        return analyzer

    @pytest.fixture
    def conflict_detector(self, mock_spacy_analyzer):
        """Create a ConflictDetector instance."""
        return ConflictDetector(mock_spacy_analyzer)

    @pytest.mark.asyncio
    async def test_detect_conflicts_empty_documents(self, conflict_detector):
        """Test conflict detection with empty document list."""
        conflicts = await conflict_detector.detect_conflicts([])

        assert conflicts.conflicting_pairs == []
        assert conflicts.conflict_categories == {}

    @pytest.mark.asyncio
    async def test_detect_conflicts_single_document(self, conflict_detector):
        """Test conflict detection with single document."""
        doc = create_hybrid_search_result(
            score=0.8,
            text="Test document",
            source_type="confluence",
            source_title="Single Doc",
        )

        conflicts = await conflict_detector.detect_conflicts([doc])

        assert conflicts.conflicting_pairs == []  # Can't have conflicts with one doc

    @pytest.mark.asyncio
    async def test_detect_conflicts_very_short_text(self, conflict_detector):
        """Test conflict detection with very short text."""
        docs = [
            create_hybrid_search_result(
                score=0.8,
                text="A",  # Very short
                source_type="confluence",
                source_title="Doc 1",
            ),
            create_hybrid_search_result(
                score=0.8,
                text="B",  # Very short
                source_type="confluence",
                source_title="Doc 2",
            ),
        ]

        conflicts = await conflict_detector.detect_conflicts(docs)

        # Should handle gracefully
        assert isinstance(conflicts.conflicting_pairs, list)

    @pytest.mark.asyncio
    async def test_detect_conflicts_identical_documents(self, conflict_detector):
        """Test conflict detection with identical documents."""
        text = "This is identical text in both documents."
        docs = [
            create_hybrid_search_result(
                score=0.8, text=text, source_type="confluence", source_title="Doc 1"
            ),
            create_hybrid_search_result(
                score=0.8,
                text=text,  # Identical text
                source_type="confluence",
                source_title="Doc 2",
            ),
        ]

        conflicts = await conflict_detector.detect_conflicts(docs)

        # Should skip identical documents
        assert len(conflicts.conflicting_pairs) == 0

    def test_should_analyze_for_conflicts_edge_cases(self, conflict_detector):
        """Test _should_analyze_for_conflicts with edge cases."""
        # Very short text
        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Hi",  # Too short
            source_type="confluence",
            source_title="Doc 1",
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Long enough text for analysis",
            source_type="confluence",
            source_title="Doc 2",
        )

        should_analyze = conflict_detector._should_analyze_for_conflicts(doc1, doc2)
        assert not should_analyze

        # Empty text
        doc3 = create_hybrid_search_result(
            score=0.8, text="", source_type="confluence", source_title="Doc 3"
        )

        should_analyze = conflict_detector._should_analyze_for_conflicts(doc3, doc2)
        assert not should_analyze

        # None text
        doc4 = create_hybrid_search_result(
            score=0.8, text=None, source_type="confluence", source_title="Doc 4"
        )

        should_analyze = conflict_detector._should_analyze_for_conflicts(doc4, doc2)
        assert not should_analyze

    def test_find_contradiction_patterns_no_patterns(self, conflict_detector):
        """Test finding contradiction patterns when none exist."""
        doc1 = create_hybrid_search_result(
            score=0.8,
            text="This document discusses authentication methods.",
            source_type="confluence",
            source_title="Doc 1",
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="This document talks about database design.",
            source_type="confluence",
            source_title="Doc 2",
        )

        patterns = conflict_detector._find_contradiction_patterns(doc1, doc2)

        assert patterns == []

    def test_categorize_conflict_unknown_indicators(self, conflict_detector):
        """Test conflict categorization with unknown indicators."""
        unknown_indicators = ["unknown pattern", "unrecognized conflict"]

        category = conflict_detector._categorize_conflict(unknown_indicators)

        assert category == "general"  # Should default to general category

    def test_calculate_conflict_confidence_empty_indicators(self, conflict_detector):
        """Test confidence calculation with empty indicators."""
        confidence = conflict_detector._calculate_conflict_confidence([])

        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_analyze_conflicts_timeout(self, conflict_detector):
        """Test LLM analysis timeout handling."""
        # Mock OpenAI client to raise TimeoutError
        conflict_detector.openai_client = AsyncMock()
        conflict_detector.openai_client.chat.completions.create.side_effect = (
            TimeoutError()
        )

        doc1 = create_hybrid_search_result(
            score=0.8,
            text="Token expires in 24 hours",
            source_type="confluence",
            source_title="Doc 1",
        )
        doc2 = create_hybrid_search_result(
            score=0.8,
            text="Token expires in 4 hours",
            source_type="confluence",
            source_title="Doc 2",
        )

        result = await conflict_detector._llm_analyze_conflicts(doc1, doc2, 0.8)

        assert result is None  # Should handle timeout gracefully

    @pytest.mark.asyncio
    async def test_llm_analyze_conflicts_no_openai_client(self, conflict_detector):
        """Test LLM analysis when no OpenAI client is configured."""
        conflict_detector.openai_client = None

        doc1 = create_hybrid_search_result(
            score=0.8, text="Test", source_type="confluence", source_title="Doc 1"
        )
        doc2 = create_hybrid_search_result(
            score=0.8, text="Test", source_type="confluence", source_title="Doc 2"
        )

        result = await conflict_detector._llm_analyze_conflicts(doc1, doc2, 0.8)

        assert result is None  # Should handle gracefully when no client
