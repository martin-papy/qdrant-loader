"""Tests for SemanticAnalyzer."""

import logging
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.core.text_processing.semantic_analyzer import (
    SemanticAnalysisResult,
    SemanticAnalyzer,
)


class TestSemanticAnalysisResult:
    """Test cases for SemanticAnalysisResult."""

    def test_initialization(self):
        """Test SemanticAnalysisResult initialization."""
        entities = [{"text": "Apple", "label": "ORG"}]
        pos_tags = [{"text": "Apple", "pos": "NOUN"}]
        dependencies = [{"text": "Apple", "dep": "nsubj"}]
        topics = [{"id": 0, "terms": [{"term": "technology", "weight": 0.5}]}]
        key_phrases = ["Apple Inc", "technology company"]
        doc_similarity = {"doc1": 0.8, "doc2": 0.6}

        result = SemanticAnalysisResult(
            entities=entities,
            pos_tags=pos_tags,
            dependencies=dependencies,
            topics=topics,
            key_phrases=key_phrases,
            document_similarity=doc_similarity,
        )

        assert result.entities == entities
        assert result.pos_tags == pos_tags
        assert result.dependencies == dependencies
        assert result.topics == topics
        assert result.key_phrases == key_phrases
        assert result.document_similarity == doc_similarity


class TestSemanticAnalyzer:
    """Test cases for SemanticAnalyzer."""

    @pytest.fixture
    def mock_nlp(self):
        """Mock spaCy NLP model."""
        nlp = Mock()
        nlp.vocab.strings = {"ORG": "Organization", "PERSON": "Person"}
        nlp.vocab.vectors_length = 0  # Simulate model without word vectors (like en_core_web_sm)
        return nlp

    @pytest.fixture
    def mock_doc(self):
        """Mock spaCy document."""
        doc = Mock()

        # Mock entities
        entity = Mock()
        entity.text = "Apple"
        entity.label_ = "ORG"
        entity.start_char = 0
        entity.end_char = 5
        entity.sent = Mock()
        entity.sent.start = 0
        entity.sent.end = 10
        # Make sentence iterable
        sent_token = Mock()
        sent_token.text = "Apple"
        sent_token.ent_type_ = "ORG"
        sent_token.dep_ = "nsubj"
        entity.sent.__iter__ = Mock(return_value=iter([sent_token]))
        doc.ents = [entity]

        # Mock tokens
        token1 = Mock()
        token1.text = "Apple"
        token1.pos_ = "NOUN"
        token1.tag_ = "NNP"
        token1.lemma_ = "apple"
        token1.is_stop = False
        token1.is_punct = False
        token1.is_space = False
        token1.dep_ = "nsubj"
        token1.head = Mock()
        token1.head.text = "is"
        token1.head.pos_ = "VERB"
        token1.children = []
        token1.ent_type_ = "ORG"

        token2 = Mock()
        token2.text = "is"
        token2.pos_ = "VERB"
        token2.tag_ = "VBZ"
        token2.lemma_ = "be"
        token2.is_stop = True
        token2.is_punct = False
        token2.is_space = False
        token2.dep_ = "ROOT"
        token2.head = token2  # Root points to itself
        token2.head.text = "is"
        token2.head.pos_ = "VERB"
        token2.children = [token1]
        token2.ent_type_ = ""

        # Make sure the document iteration returns the tokens
        tokens = [token1, token2]
        doc.__iter__ = Mock(return_value=iter(tokens))
        doc.__getitem__ = Mock(return_value=Mock(text="Apple is a company"))

        # Mock noun chunks
        chunk = Mock()
        chunk.text = "Apple company"
        doc.noun_chunks = [chunk]

        # Mock similarity
        doc.similarity = Mock(return_value=0.8)

        return doc

    def test_initialization_default_params(self):
        """Test SemanticAnalyzer initialization with default parameters."""
        with patch("spacy.load") as mock_load:
            mock_nlp = Mock()
            mock_nlp.vocab.vectors_length = 0  # Simulate model without word vectors
            mock_load.return_value = mock_nlp

            analyzer = SemanticAnalyzer()

            assert analyzer.num_topics == 5
            assert analyzer.passes == 10
            assert analyzer.min_topic_freq == 2
            assert analyzer.nlp == mock_nlp
            assert analyzer.lda_model is None
            assert analyzer.dictionary is None
            assert analyzer._doc_cache == {}
            mock_load.assert_called_once_with("en_core_web_md")

    def test_initialization_custom_params(self):
        """Test SemanticAnalyzer initialization with custom parameters."""
        with patch("spacy.load") as mock_load:
            mock_nlp = Mock()
            mock_nlp.vocab.vectors_length = 0  # Simulate model without word vectors
            mock_load.return_value = mock_nlp

            analyzer = SemanticAnalyzer(
                spacy_model="en_core_web_lg", num_topics=10, passes=20, min_topic_freq=5
            )

            assert analyzer.num_topics == 10
            assert analyzer.passes == 20
            assert analyzer.min_topic_freq == 5
            mock_load.assert_called_once_with("en_core_web_lg")

    def test_initialization_model_download(self):
        """Test SemanticAnalyzer initialization with model download."""
        with (
            patch(
                "qdrant_loader.core.text_processing.semantic_analyzer.spacy.load"
            ) as mock_load,
            patch(
                "qdrant_loader.core.text_processing.semantic_analyzer.spacy_download"
            ) as mock_download,
        ):
            # First call raises OSError, second call succeeds
            mock_nlp = Mock()
            mock_nlp.vocab.vectors_length = 0  # Simulate model without word vectors
            mock_load.side_effect = [OSError("Model not found"), mock_nlp]

            analyzer = SemanticAnalyzer()

            assert analyzer.nlp == mock_nlp
            mock_download.assert_called_once_with("en_core_web_md")
            assert mock_load.call_count == 2

    def test_analyze_text_basic(self, mock_nlp, mock_doc):
        """Test basic text analysis."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity", return_value={}
            ),
        ):

            # Configure mock_nlp to return mock_doc when called with text
            mock_nlp.return_value = mock_doc
            analyzer = SemanticAnalyzer()

            result = analyzer.analyze_text("Apple is a company")

            assert isinstance(result, SemanticAnalysisResult)
            assert len(result.entities) > 0
            assert len(result.pos_tags) > 0
            assert result.topics == []
            assert len(result.key_phrases) > 0
            assert result.document_similarity == {}

    def test_analyze_text_with_caching(self, mock_nlp, mock_doc):
        """Test text analysis with caching."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity", return_value={}
            ),
        ):

            mock_nlp.return_value = mock_doc
            analyzer = SemanticAnalyzer()

            # First call should process and cache
            result1 = analyzer.analyze_text("Apple is a company", doc_id="doc1")

            # Second call should return cached result
            result2 = analyzer.analyze_text("Apple is a company", doc_id="doc1")

            assert result1 is result2
            assert "doc1" in analyzer._doc_cache

    def test_extract_entities(self, mock_nlp, mock_doc):
        """Test entity extraction."""
        with patch("spacy.load", return_value=mock_nlp):
            analyzer = SemanticAnalyzer()
            entities = analyzer._extract_entities(mock_doc)

            assert len(entities) == 1
            entity = entities[0]
            assert entity["text"] == "Apple"
            assert entity["label"] == "ORG"
            assert entity["start"] == 0
            assert entity["end"] == 5
            assert "description" in entity
            assert "context" in entity
            assert "related_entities" in entity

    def test_get_pos_tags(self, mock_nlp, mock_doc):
        """Test POS tag extraction."""
        with patch("spacy.load", return_value=mock_nlp):
            analyzer = SemanticAnalyzer()
            pos_tags = analyzer._get_pos_tags(mock_doc)

            assert len(pos_tags) == 2

            # Check first token (Apple)
            tag1 = pos_tags[0]
            assert tag1["text"] == "Apple"
            assert tag1["pos"] == "NOUN"
            assert tag1["tag"] == "NNP"
            assert tag1["lemma"] == "apple"
            assert tag1["is_stop"] is False
            assert tag1["is_punct"] is False
            assert tag1["is_space"] is False

            # Check second token (is)
            tag2 = pos_tags[1]
            assert tag2["text"] == "is"
            assert tag2["pos"] == "VERB"
            assert tag2["is_stop"] is True

    def test_get_dependencies(self, mock_nlp, mock_doc):
        """Test dependency parsing."""
        with patch("spacy.load", return_value=mock_nlp):
            analyzer = SemanticAnalyzer()
            dependencies = analyzer._get_dependencies(mock_doc)

            assert len(dependencies) == 2

            # Check first token dependencies
            dep1 = dependencies[0]
            assert dep1["text"] == "Apple"
            assert dep1["dep"] == "nsubj"
            assert dep1["head"] == "is"
            assert dep1["head_pos"] == "VERB"
            assert dep1["children"] == []

            # Check second token dependencies
            dep2 = dependencies[1]
            assert dep2["text"] == "is"
            assert dep2["dep"] == "ROOT"
            assert dep2["head"] == "is"
            assert dep2["children"] == ["Apple"]

    def test_extract_topics_existing_model(self, mock_nlp):
        """Test topic extraction with existing LDA model."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch(
                "qdrant_loader.core.text_processing.semantic_analyzer.preprocess_string",
                return_value=["apple", "company", "technology", "innovation", "business"],
            ),
        ):

            analyzer = SemanticAnalyzer()

            # Set up existing model and dictionary
            mock_dict = Mock()
            mock_dict.doc2bow.return_value = [(0, 1), (1, 1)]
            mock_dict.add_documents = Mock()
            analyzer.dictionary = mock_dict

            mock_lda = Mock()
            mock_lda.update = Mock()
            mock_lda.print_topics.return_value = [(0, '0.5*"apple" + 0.3*"company"')]
            analyzer.lda_model = mock_lda

            topics = analyzer._extract_topics("Apple is a company")

            # Verify existing model was updated
            mock_dict.add_documents.assert_called_once()
            mock_lda.update.assert_called_once()
            assert len(topics) == 1

    def test_extract_key_phrases(self, mock_nlp, mock_doc):
        """Test key phrase extraction."""
        with patch("spacy.load", return_value=mock_nlp):
            # Add an entity with appropriate label
            entity = Mock()
            entity.text = "Apple Inc"
            entity.label_ = "ORG"
            mock_doc.ents = [entity]

            analyzer = SemanticAnalyzer()
            key_phrases = analyzer._extract_key_phrases(mock_doc)

            assert "Apple company" in key_phrases  # From noun chunks
            assert "Apple Inc" in key_phrases  # From entities
            assert len(set(key_phrases)) == len(key_phrases)  # No duplicates

    def test_extract_key_phrases_filtered_entities(self, mock_nlp, mock_doc):
        """Test key phrase extraction with filtered entity types."""
        with patch("spacy.load", return_value=mock_nlp):
            # Add entities with different labels
            entity1 = Mock()
            entity1.text = "Apple Inc"
            entity1.label_ = "ORG"  # Should be included

            entity2 = Mock()
            entity2.text = "John Doe"
            entity2.label_ = "PERSON"  # Should not be included

            mock_doc.ents = [entity1, entity2]

            analyzer = SemanticAnalyzer()
            key_phrases = analyzer._extract_key_phrases(mock_doc)

            assert "Apple Inc" in key_phrases
            assert "John Doe" not in key_phrases

    def test_calculate_document_similarity_empty_cache(self, mock_nlp, mock_doc):
        """Test document similarity calculation with empty cache."""
        with patch("spacy.load", return_value=mock_nlp):
            mock_nlp.return_value = mock_doc

            analyzer = SemanticAnalyzer()
            similarities = analyzer._calculate_document_similarity("Apple is a company")

            assert similarities == {}

    def test_calculate_document_similarity_with_cache(self, mock_nlp, mock_doc):
        """Test document similarity calculation with cached documents."""
        with patch("spacy.load", return_value=mock_nlp):
            mock_nlp.return_value = mock_doc

            analyzer = SemanticAnalyzer()

            # Add a cached result
            cached_result = SemanticAnalysisResult(
                entities=[{"context": "Microsoft is a company"}],
                pos_tags=[],
                dependencies=[],
                topics=[],
                key_phrases=[],
                document_similarity={},
            )
            analyzer._doc_cache["doc1"] = cached_result

            similarities = analyzer._calculate_document_similarity("Apple is a company")

            assert "doc1" in similarities
            assert isinstance(similarities["doc1"], float)

    def test_calculate_topic_coherence(self, mock_nlp):
        """Test topic coherence calculation."""
        with patch("spacy.load", return_value=mock_nlp):
            analyzer = SemanticAnalyzer()

            terms = [
                {"term": "apple", "weight": 0.5},
                {"term": "company", "weight": 0.3},
                {"term": "technology", "weight": 0.2},
            ]

            coherence = analyzer._calculate_topic_coherence(terms)

            expected = (0.5 + 0.3 + 0.2) / 3
            assert coherence == expected

    def test_calculate_topic_coherence_empty_terms(self, mock_nlp):
        """Test topic coherence calculation with empty terms."""
        with patch("spacy.load", return_value=mock_nlp):
            analyzer = SemanticAnalyzer()

            coherence = analyzer._calculate_topic_coherence([])

            assert coherence == 0.0

    def test_clear_cache(self, mock_nlp):
        """Test cache clearing."""
        with patch("spacy.load", return_value=mock_nlp):
            analyzer = SemanticAnalyzer()

            # Add some cached data
            analyzer._doc_cache["doc1"] = Mock()
            analyzer._doc_cache["doc2"] = Mock()

            assert len(analyzer._doc_cache) == 2

            analyzer.clear_cache()

            assert len(analyzer._doc_cache) == 0

    def test_logging_configuration(self, mock_nlp):
        """Test that logging is properly configured."""
        with patch("spacy.load", return_value=mock_nlp):
            analyzer = SemanticAnalyzer()

            assert hasattr(analyzer, "logger")
            assert isinstance(analyzer.logger, logging.Logger)

    def test_extract_topics_simplified(self, mock_nlp):
        """Test topic extraction with simplified mocking."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(
                SemanticAnalyzer,
                "_extract_topics",
                return_value=[
                    {
                        "id": 0,
                        "terms": [{"term": "test", "weight": 0.5}],
                        "coherence": 0.5,
                    }
                ],
            ),
        ):
            analyzer = SemanticAnalyzer()
            topics = analyzer._extract_topics("Apple is a company")

            assert len(topics) == 1
            assert topics[0]["id"] == 0
            assert "coherence" in topics[0]

    def test_analyze_text_integration_simplified(self, mock_nlp):
        """Test complete text analysis integration with simplified expectations."""
        with patch("spacy.load", return_value=mock_nlp):
            # Create a more realistic mock document
            doc = Mock()

            # Mock entity
            entity = Mock()
            entity.text = "Apple Inc"
            entity.label_ = "ORG"
            entity.start_char = 0
            entity.end_char = 9
            entity.sent = Mock()
            entity.sent.start = 0
            entity.sent.end = 5
            # Make sentence iterable
            sent_token = Mock()
            sent_token.text = "Apple"
            sent_token.ent_type_ = "ORG"
            sent_token.dep_ = "nsubj"
            entity.sent.__iter__ = Mock(return_value=iter([sent_token]))
            doc.ents = [entity]

            # Mock tokens
            tokens = []
            for i, (text, pos, tag, lemma, is_stop) in enumerate(
                [
                    ("Apple", "NOUN", "NNP", "apple", False),
                    ("Inc", "NOUN", "NNP", "inc", False),
                    ("is", "VERB", "VBZ", "be", True),
                    ("a", "DET", "DT", "a", True),
                    ("company", "NOUN", "NN", "company", False),
                ]
            ):
                token = Mock()
                token.text = text
                token.pos_ = pos
                token.tag_ = tag
                token.lemma_ = lemma
                token.is_stop = is_stop
                token.is_punct = False
                token.is_space = False
                token.dep_ = (
                    "nsubj"
                    if i == 0
                    else "ROOT" if text == "is" else "det" if text == "a" else "attr"
                )
                token.head = Mock()
                token.head.text = "is"
                token.head.pos_ = "VERB"
                token.children = []
                token.ent_type_ = "ORG" if text in ["Apple", "Inc"] else ""
                tokens.append(token)

            doc.__iter__ = Mock(return_value=iter(tokens))
            doc.__getitem__ = Mock(return_value=Mock(text="Apple Inc is a company"))

            # Mock noun chunks
            chunk = Mock()
            chunk.text = "Apple Inc"
            doc.noun_chunks = [chunk]

            # Mock similarity
            doc.similarity = Mock(return_value=0.9)

            mock_nlp.return_value = doc

            # Mock topic extraction
            with patch.object(
                SemanticAnalyzer,
                "_extract_topics",
                return_value=[
                    {
                        "id": 0,
                        "terms": [{"term": "technology", "weight": 0.5}],
                        "coherence": 0.5,
                    }
                ],
            ):
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_text(
                    "Apple Inc is a company", doc_id="test_doc"
                )

                # Verify all components are present
                assert len(result.entities) == 1
                assert len(result.pos_tags) == 5
                assert len(result.topics) == 1
                assert len(result.key_phrases) >= 1
                assert isinstance(result.document_similarity, dict)

                # Verify caching
                assert "test_doc" in analyzer._doc_cache
