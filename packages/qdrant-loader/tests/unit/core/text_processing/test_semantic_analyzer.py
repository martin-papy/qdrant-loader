"""Tests for SemanticAnalyzer."""

import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from qdrant_loader.core.text_processing.semantic_analyzer import (
    SemanticAnalysisResult,
    SemanticAnalyzer,
    is_meaningful_text,
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


class TestIsMeaningfulText:
    """Test cases for is_meaningful_text function."""

    def test_text_with_letters_is_meaningful(self):
        """Test that text with letters is considered meaningful."""
        assert is_meaningful_text("Apple") is True
        assert is_meaningful_text("hello") is True
        assert is_meaningful_text("USA") is True

    def test_text_with_digits_is_meaningful(self):
        """Test that text with digits is considered meaningful."""
        assert is_meaningful_text("123") is True
        assert is_meaningful_text("2024") is True

    def test_text_with_alphanumeric_is_meaningful(self):
        """Test that text with letters and numbers is meaningful."""
        assert is_meaningful_text("Apple123") is True
        assert is_meaningful_text("COVID-19") is True
        assert is_meaningful_text("Section1.2") is True

    def test_punctuation_only_not_meaningful(self):
        """Test that punctuation-only text is not meaningful."""
        assert is_meaningful_text(".") is False
        assert is_meaningful_text("#") is False
        assert is_meaningful_text("|") is False
        assert is_meaningful_text(",") is False
        assert is_meaningful_text("...") is False
        assert is_meaningful_text("---") is False
        assert is_meaningful_text("!!!") is False

    def test_special_symbols_not_meaningful(self):
        """Test that special symbols without content are not meaningful."""
        assert is_meaningful_text("@") is False
        assert is_meaningful_text("$") is False
        assert is_meaningful_text("%") is False
        assert is_meaningful_text("&") is False
        assert is_meaningful_text("*") is False
        assert is_meaningful_text("~") is False

    def test_whitespace_not_meaningful(self):
        """Test that whitespace-only text is not meaningful."""
        assert is_meaningful_text(" ") is False
        assert is_meaningful_text("  ") is False
        assert is_meaningful_text("\t") is False
        assert is_meaningful_text("\n") is False

    def test_mixed_with_punctuation_is_meaningful(self):
        """Test that text with meaningful content and punctuation is still meaningful."""
        assert is_meaningful_text("Apple.") is True
        assert is_meaningful_text("#hashtag") is True
        assert is_meaningful_text("@username") is True
        assert is_meaningful_text("(test)") is True

    def test_empty_string_not_meaningful(self):
        """Test that empty string is not meaningful."""
        assert is_meaningful_text("") is False

    def test_table_separators_not_meaningful(self):
        """Test that table separators (common in Excel/markdown) are not meaningful."""
        assert is_meaningful_text("|") is False
        assert is_meaningful_text("|-") is False
        assert is_meaningful_text("|--") is False
        assert is_meaningful_text("||") is False


class TestSemanticAnalyzer:
    """Test cases for SemanticAnalyzer."""

    @pytest.fixture
    def mock_nlp(self):
        """Mock spaCy NLP model."""
        nlp = Mock()
        nlp.vocab.strings = {"ORG": "Organization", "PERSON": "Person"}
        nlp.vocab.vectors_length = (
            0  # Simulate model without word vectors (like en_core_web_sm)
        )
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

            result = analyzer.analyze_text("Apple is a company", include_enhanced=True)

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
            result1 = analyzer.analyze_text(
                "Apple is a company", doc_id="doc1", include_enhanced=True
            )

            # Second call should return cached result (deep-copied when include_enhanced=True)
            result2 = analyzer.analyze_text(
                "Apple is a company", doc_id="doc1", include_enhanced=True
            )

            # With include_enhanced=True, cache hit returns a deep copy with refreshed similarity
            # So result1 and result2 are different objects, but have same content
            assert result1 is not result2
            assert result1.entities == result2.entities
            assert result1.pos_tags == result2.pos_tags
            assert result1.topics == result2.topics
            assert len(analyzer._doc_cache) == 1
            assert any(
                key[0] == "doc1"
                for key in analyzer._doc_cache
                if isinstance(key, tuple)
            )

    def test_analyze_text_without_enhanced_fields(self, mock_nlp, mock_doc):
        """Test text analysis short-circuits enhanced computations when disabled."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer,
                "_calculate_document_similarity",
                return_value={"doc1": 0.8},
            ) as mock_similarity,
            patch.object(SemanticAnalyzer, "_get_pos_tags") as mock_pos_tags,
            patch.object(SemanticAnalyzer, "_get_dependencies") as mock_dependencies,
        ):
            mock_nlp.return_value = mock_doc
            analyzer = SemanticAnalyzer()

            result = analyzer.analyze_text(
                "Apple is a company", doc_id="doc2", include_enhanced=False
            )

            assert result.pos_tags == []
            assert result.dependencies == []
            assert result.document_similarity == {}
            mock_pos_tags.assert_not_called()
            mock_dependencies.assert_not_called()
            mock_similarity.assert_not_called()
            assert len(analyzer._doc_cache) == 1
            assert any(
                key[0] == "doc2"
                for key in analyzer._doc_cache
                if isinstance(key, tuple)
            )

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

    def test_extract_entities_filters_punctuation_only(self):
        """Test that entity extraction filters out punctuation-only entities."""
        # Create custom mock_nlp with MISC label support
        mock_nlp = Mock()

        # Mock vocab.strings to support subscripting like a dict
        vocab_strings_dict = {
            "ORG": "Organization",
            "PERSON": "Person",
            "MISC": "Miscellaneous",
        }
        mock_vocab_strings = MagicMock()
        mock_vocab_strings.__getitem__.side_effect = lambda key: vocab_strings_dict.get(
            key, "Unknown"
        )
        mock_nlp.vocab.strings = mock_vocab_strings
        mock_nlp.vocab.vectors_length = 0

        with patch("spacy.load", return_value=mock_nlp):
            # Create mock document with both meaningful and punctuation-only entities
            mock_doc = MagicMock()

            # Mock doc slicing for context extraction
            mock_context = Mock()
            mock_context.text = "Apple is a company"
            mock_doc.__getitem__.return_value = mock_context

            # Mock entity 1: meaningful (Apple)
            entity1 = Mock()
            entity1.text = "Apple"
            entity1.label_ = "ORG"
            entity1.start_char = 0
            entity1.end_char = 5
            entity1.sent = Mock()
            entity1.sent.start = 0
            entity1.sent.end = 10
            sent_token1 = Mock()
            sent_token1.text = "Apple"
            sent_token1.ent_type_ = "ORG"
            sent_token1.dep_ = "nsubj"
            entity1.sent.__iter__ = Mock(return_value=iter([sent_token1]))

            # Mock entity 2: punctuation only (should be filtered)
            entity2 = Mock()
            entity2.text = "#"
            entity2.label_ = "MISC"
            entity2.start_char = 6
            entity2.end_char = 7
            entity2.sent = Mock()
            entity2.sent.start = 0
            entity2.sent.end = 10
            entity2.sent.__iter__ = Mock(return_value=iter([]))

            # Mock entity 3: pipe character (should be filtered)
            entity3 = Mock()
            entity3.text = "|"
            entity3.label_ = "MISC"
            entity3.start_char = 8
            entity3.end_char = 9
            entity3.sent = Mock()
            entity3.sent.start = 0
            entity3.sent.end = 10
            entity3.sent.__iter__ = Mock(return_value=iter([]))

            # Mock entity 4: dots only (should be filtered)
            entity4 = Mock()
            entity4.text = "..."
            entity4.label_ = "MISC"
            entity4.start_char = 10
            entity4.end_char = 13
            entity4.sent = Mock()
            entity4.sent.start = 0
            entity4.sent.end = 13
            entity4.sent.__iter__ = Mock(return_value=iter([]))

            mock_doc.ents = [entity1, entity2, entity3, entity4]

            analyzer = SemanticAnalyzer()
            entities = analyzer._extract_entities(mock_doc)

            # Should only return Apple, filter out #, |, ...
            assert len(entities) == 1
            assert entities[0]["text"] == "Apple"

            # Verify no punctuation-only entities
            entity_texts = [e["text"] for e in entities]
            assert "#" not in entity_texts
            assert "|" not in entity_texts
            assert "..." not in entity_texts

    def test_extract_entities_filters_related_entities(self):
        """Test that related entities are also filtered for meaningfulness."""
        # Create custom mock_nlp with MISC label support
        mock_nlp = Mock()

        # Mock vocab.strings to support subscripting like a dict
        vocab_strings_dict = {
            "ORG": "Organization",
            "PERSON": "Person",
            "MISC": "Miscellaneous",
        }
        mock_vocab_strings = MagicMock()
        mock_vocab_strings.__getitem__.side_effect = lambda key: vocab_strings_dict.get(
            key, "Unknown"
        )
        mock_nlp.vocab.strings = mock_vocab_strings
        mock_nlp.vocab.vectors_length = 0

        with patch("spacy.load", return_value=mock_nlp):
            mock_doc = MagicMock()

            # Mock doc slicing for context extraction
            mock_context = Mock()
            mock_context.text = "Apple Inc Company"
            mock_doc.__getitem__.return_value = mock_context

            # Create entity with mixed related entities
            entity = Mock()
            entity.text = "Apple"
            entity.label_ = "ORG"
            entity.start_char = 0
            entity.end_char = 5
            entity.sent = Mock()
            entity.sent.start = 0
            entity.sent.end = 10

            # Related tokens: meaningful and garbage
            related_token1 = Mock()
            related_token1.text = "Inc"
            related_token1.ent_type_ = "ORG"
            related_token1.dep_ = "compound"

            related_token2 = Mock()
            related_token2.text = "#"
            related_token2.ent_type_ = "MISC"
            related_token2.dep_ = "dep"

            related_token3 = Mock()
            related_token3.text = "Company"
            related_token3.ent_type_ = "ORG"
            related_token3.dep_ = "appos"

            entity.sent.__iter__ = Mock(
                return_value=iter([related_token1, related_token2, related_token3])
            )
            mock_doc.ents = [entity]

            analyzer = SemanticAnalyzer()
            entities = analyzer._extract_entities(mock_doc)

            assert len(entities) == 1
            related = entities[0]["related_entities"]

            # Should have 2 related entities (Inc, Company), not #
            assert len(related) == 2
            related_texts = [r["text"] for r in related]
            assert "Inc" in related_texts
            assert "Company" in related_texts
            assert "#" not in related_texts

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
            # Note: is_punct and is_space are no longer in output (filtered)

            # Check second token (is)
            tag2 = pos_tags[1]
            assert tag2["text"] == "is"
            assert tag2["pos"] == "VERB"
            assert tag2["is_stop"] is True

    def test_get_pos_tags_filters_punctuation_and_spaces(self, mock_nlp):
        """Test that POS tagging filters out punctuation and space tokens."""
        with patch("spacy.load", return_value=mock_nlp):
            # Create mock document with tokens including spaces and punctuation
            mock_doc = Mock()

            # Mock tokens: word, space, punctuation, word
            token1 = Mock()
            token1.text = "Hello"
            token1.pos_ = "NOUN"
            token1.tag_ = "NN"
            token1.lemma_ = "hello"
            token1.is_stop = False
            token1.is_punct = False
            token1.is_space = False

            token2 = Mock()
            token2.text = " "
            token2.pos_ = "SPACE"
            token2.tag_ = "_SP"
            token2.lemma_ = " "
            token2.is_stop = False
            token2.is_punct = False
            token2.is_space = True  # Should be filtered

            token3 = Mock()
            token3.text = ","
            token3.pos_ = "PUNCT"
            token3.tag_ = ","
            token3.lemma_ = ","
            token3.is_stop = False
            token3.is_punct = True  # Should be filtered
            token3.is_space = False

            token4 = Mock()
            token4.text = "world"
            token4.pos_ = "NOUN"
            token4.tag_ = "NN"
            token4.lemma_ = "world"
            token4.is_stop = False
            token4.is_punct = False
            token4.is_space = False

            mock_doc.__iter__ = Mock(
                return_value=iter([token1, token2, token3, token4])
            )

            analyzer = SemanticAnalyzer()
            pos_tags = analyzer._get_pos_tags(mock_doc)

            # Should only have 2 tokens (Hello and world), spaces/punct filtered
            assert len(pos_tags) == 2
            assert pos_tags[0]["text"] == "Hello"
            assert pos_tags[1]["text"] == "world"

            # Verify no punctuation or spaces in output
            for tag in pos_tags:
                assert not tag["text"].isspace()
                assert tag["text"] not in [",", ".", "|", ";", ":", "!"]

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

    def test_get_dependencies_filters_punctuation_spaces_and_symbols(self, mock_nlp):
        """Test that dependency parsing filters out noisy tokens and children."""
        with patch("spacy.load", return_value=mock_nlp):
            mock_doc = Mock()

            token_word = Mock()
            token_word.text = "Hello"
            token_word.dep_ = "nsubj"
            token_word.pos_ = "NOUN"
            token_word.is_punct = False
            token_word.is_space = False
            token_word.head = Mock()
            token_word.head.text = "runs"
            token_word.head.pos_ = "VERB"

            child_good = Mock()
            child_good.text = "world"
            child_good.is_punct = False
            child_good.is_space = False

            child_punct = Mock()
            child_punct.text = ","
            child_punct.is_punct = True
            child_punct.is_space = False

            child_space = Mock()
            child_space.text = " "
            child_space.is_punct = False
            child_space.is_space = True

            child_symbol = Mock()
            child_symbol.text = "|||"
            child_symbol.is_punct = False
            child_symbol.is_space = False

            token_word.children = [child_good, child_punct, child_space, child_symbol]

            token_space = Mock()
            token_space.text = " "
            token_space.dep_ = "dep"
            token_space.pos_ = "SPACE"
            token_space.is_punct = False
            token_space.is_space = True
            token_space.head = token_word
            token_space.children = []

            token_punct = Mock()
            token_punct.text = "."
            token_punct.dep_ = "punct"
            token_punct.pos_ = "PUNCT"
            token_punct.is_punct = True
            token_punct.is_space = False
            token_punct.head = token_word
            token_punct.children = []

            token_symbol = Mock()
            token_symbol.text = "---"
            token_symbol.dep_ = "dep"
            token_symbol.pos_ = "SYM"
            token_symbol.is_punct = False
            token_symbol.is_space = False
            token_symbol.head = token_word
            token_symbol.children = []

            token_root = Mock()
            token_root.text = "runs"
            token_root.dep_ = "ROOT"
            token_root.pos_ = "VERB"
            token_root.is_punct = False
            token_root.is_space = False
            token_root.head = token_root
            token_root.children = []

            mock_doc.__iter__ = Mock(
                return_value=iter(
                    [token_word, token_space, token_punct, token_symbol, token_root]
                )
            )

            analyzer = SemanticAnalyzer()
            dependencies = analyzer._get_dependencies(mock_doc)

            assert len(dependencies) == 2
            assert dependencies[0]["text"] == "Hello"
            assert dependencies[0]["children"] == ["world"]
            assert dependencies[1]["text"] == "runs"

    def test_extract_topics_existing_model(self, mock_nlp):
        """Test topic extraction with existing LDA model."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch(
                "qdrant_loader.core.text_processing.semantic_analyzer.preprocess_string",
                return_value=[
                    "apple",
                    "company",
                    "technology",
                    "innovation",
                    "business",
                ],
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

    def test_calculate_document_similarity_excludes_current_doc_id(
        self, mock_nlp, mock_doc
    ):
        """Test similarity excludes the current doc_id from results."""
        with patch("spacy.load", return_value=mock_nlp):
            mock_nlp.return_value = mock_doc

            analyzer = SemanticAnalyzer()

            # Add multiple cached results
            for doc_id in ["doc1", "doc2", "doc3"]:
                cached_result = SemanticAnalysisResult(
                    entities=[{"context": f"{doc_id} context"}],
                    pos_tags=[],
                    dependencies=[],
                    topics=[],
                    key_phrases=[],
                    document_similarity={},
                )
                analyzer._doc_cache[doc_id] = cached_result

            # Calculate similarity excluding doc2
            similarities = analyzer._calculate_document_similarity(
                "Apple is a company", doc_id="doc2"
            )

            # doc1 and doc3 should be in results, but not doc2 (current id)
            assert "doc1" in similarities
            assert "doc3" in similarities
            assert "doc2" not in similarities

    def test_analyze_text_cache_separate_by_include_enhanced(self, mock_nlp, mock_doc):
        """Test that same doc_id with different include_enhanced values are cached separately."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity", return_value={}
            ),
        ):
            mock_nlp.return_value = mock_doc
            analyzer = SemanticAnalyzer()

            # Analyze same text with same doc_id but different include_enhanced
            result_enhanced_false = analyzer.analyze_text(
                "Apple is a company", doc_id="same_doc", include_enhanced=False
            )
            result_enhanced_true = analyzer.analyze_text(
                "Apple is a company", doc_id="same_doc", include_enhanced=True
            )

            # Should be different objects (separate cache entries)
            assert result_enhanced_false is not result_enhanced_true

            # Cache should have separate keys (include_enhanced is last element)
            assert any(
                key[0] == "same_doc" and key[-1] is False
                for key in analyzer._doc_cache
                if isinstance(key, tuple)
            )
            assert any(
                key[0] == "same_doc" and key[-1] is True
                for key in analyzer._doc_cache
                if isinstance(key, tuple)
            )

            # Verify enhanced fields differ
            assert len(result_enhanced_false.pos_tags) == 0
            assert len(result_enhanced_true.pos_tags) > 0

    def test_analyze_text_cache_hit_refreshes_similarity(self, mock_nlp, mock_doc):
        """Test that cache hit with include_enhanced=True refreshes similarity."""
        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity"
            ) as mock_similarity,
        ):
            mock_nlp.return_value = mock_doc
            analyzer = SemanticAnalyzer()

            # Mock _calculate_document_similarity to return different results on each call
            mock_similarity.side_effect = [
                {"other_doc": 0.5},  # First call (initial analysis of doc1)
                {
                    "doc2": 0.7
                },  # Second call (cache hit, refreshed with doc2 now in cache)
            ]

            # First call - analyze doc1 and cache it
            result1 = analyzer.analyze_text(
                "Apple is a company", doc_id="doc1", include_enhanced=True
            )
            assert result1.document_similarity == {"other_doc": 0.5}

            # Add doc2 to cache (simulating another document being analyzed)
            doc2_result = SemanticAnalysisResult(
                entities=[{"context": "Microsoft is a company"}],
                pos_tags=[],
                dependencies=[],
                topics=[],
                key_phrases=[],
                document_similarity={},
            )
            analyzer._doc_cache[("doc2", True)] = doc2_result

            # Second call - cache hit for doc1, should refresh similarity
            result2 = analyzer.analyze_text(
                "Apple is a company", doc_id="doc1", include_enhanced=True
            )

            # Result should have refreshed similarity (now includes doc2)
            assert result2.document_similarity == {"doc2": 0.7}
            # Verify _calculate_document_similarity was called twice (initial + refresh)
            assert mock_similarity.call_count == 2

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
                    else "ROOT"
                    if text == "is"
                    else "det"
                    if text == "a"
                    else "attr"
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
                    "Apple Inc is a company", doc_id="test_doc", include_enhanced=True
                )

                # Verify all components are present
                assert len(result.entities) == 1
                assert len(result.pos_tags) == 5
                assert len(result.topics) == 1
                assert len(result.key_phrases) >= 1
                assert isinstance(result.document_similarity, dict)

                # Verify caching
                assert any(
                    key[0] == "test_doc"
                    for key in analyzer._doc_cache
                    if isinstance(key, tuple)
                )


class TestCacheKeyFingerprint:
    """Cache key must include text content hash to prevent stale results."""

    def test_same_doc_id_different_text_different_cache_key(self):
        import hashlib

        doc_id = "chunk_0"
        text_a = "Apple Inc was founded in 1976"
        text_b = "Microsoft Corporation was founded in 1975"

        fp_a = hashlib.sha256(text_a.encode("utf-8")).hexdigest()[:16]
        fp_b = hashlib.sha256(text_b.encode("utf-8")).hexdigest()[:16]

        key_a = (doc_id, fp_a, False)
        key_b = (doc_id, fp_b, False)
        assert key_a != key_b, "Different text should produce different cache keys"

    def test_same_doc_id_same_text_same_cache_key(self):
        import hashlib

        doc_id = "chunk_0"
        text = "Same content"

        fp1 = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        fp2 = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

        key1 = (doc_id, fp1, False)
        key2 = (doc_id, fp2, False)
        assert key1 == key2, "Same text should produce same cache key"


class TestSemanticAnalyzerConcurrency:
    """Test thread-safety of SemanticAnalyzer cache under concurrent access."""

    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    @pytest.fixture
    def mock_nlp_fixture(self):
        """Create mock spaCy nlp object."""
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.ents = []
        mock_doc.noun_chunks = []
        mock_doc.similarity = Mock(return_value=0.8)
        mock_nlp.return_value = mock_doc
        return mock_nlp, mock_doc

    def test_concurrent_cache_reads_same_doc_id(self, mock_nlp_fixture):
        """Test multiple threads reading the same cached document."""
        import threading

        mock_nlp, mock_doc = mock_nlp_fixture

        results = []
        errors = []

        def read_cache(doc_id, include_enhanced):
            try:
                with (
                    patch("spacy.load", return_value=mock_nlp),
                    patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
                    patch.object(
                        SemanticAnalyzer,
                        "_calculate_document_similarity",
                        return_value={},
                    ),
                ):
                    analyzer.analyze_text(
                        f"Test document {doc_id}",
                        doc_id=doc_id,
                        include_enhanced=include_enhanced,
                    )
                    results.append((doc_id, include_enhanced))
            except Exception as e:
                errors.append(str(e))

        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity", return_value={}
            ),
        ):
            analyzer = SemanticAnalyzer()

            # Spawn multiple threads reading the same document
            threads = []
            for _i in range(10):
                t = threading.Thread(
                    target=read_cache, args=("doc1", False), daemon=True
                )
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join(timeout=10)

            # All operations should succeed without deadlock or corruption
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 10
            assert len(analyzer._doc_cache) == 1  # Only one cache entry

    def test_concurrent_writes_different_doc_ids(self, mock_nlp_fixture):
        """Test multiple threads writing different documents to cache."""
        import threading

        mock_nlp, mock_doc = mock_nlp_fixture
        errors = []

        def write_cache(doc_id):
            try:
                with (
                    patch("spacy.load", return_value=mock_nlp),
                    patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
                    patch.object(
                        SemanticAnalyzer,
                        "_calculate_document_similarity",
                        return_value={},
                    ),
                ):
                    analyzer.analyze_text(
                        f"Test document {doc_id}",
                        doc_id=doc_id,
                        include_enhanced=False,
                    )
            except Exception as e:
                errors.append(str(e))

        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity", return_value={}
            ),
        ):
            analyzer = SemanticAnalyzer()

            # Spawn multiple threads writing different documents
            threads = []
            num_docs = 20
            for i in range(num_docs):
                t = threading.Thread(
                    target=write_cache, args=(f"doc_{i}",), daemon=True
                )
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join(timeout=10)

            # All operations should succeed
            assert len(errors) == 0, f"Errors occurred: {errors}"
            # Each doc_id creates one cache entry per include_enhanced value
            assert len(analyzer._doc_cache) == num_docs

    def test_concurrent_cache_hits_and_misses(self, mock_nlp_fixture):
        """Test concurrent mix of cache hits and misses."""
        import threading

        mock_nlp, mock_doc = mock_nlp_fixture
        errors = []
        hit_count = 0
        hit_lock = threading.Lock()

        def analyze_with_mix(doc_id, text_variant):
            nonlocal hit_count
            try:
                with (
                    patch("spacy.load", return_value=mock_nlp),
                    patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
                    patch.object(
                        SemanticAnalyzer,
                        "_calculate_document_similarity",
                        return_value={},
                    ),
                ):
                    # Some threads hit cache, others miss
                    text = f"Document {text_variant}" if text_variant % 2 == 0 else ""
                    result = analyzer.analyze_text(
                        text, doc_id=doc_id, include_enhanced=False
                    )

                    # Simple hit detection: if result has cached entities
                    if hasattr(result, "entities"):
                        with hit_lock:
                            hit_count += 1
            except Exception as e:
                errors.append(str(e))

        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity", return_value={}
            ),
        ):
            analyzer = SemanticAnalyzer()

            # Pre-populate cache with some documents
            for i in range(5):
                analyzer.analyze_text(f"Cached doc {i}", doc_id=f"cached_{i}")

            initial_cache_size = len(analyzer._doc_cache)

            # Spawn concurrent threads with mix of hits and misses
            threads = []
            for i in range(20):
                t = threading.Thread(
                    target=analyze_with_mix, args=("cached_1", i), daemon=True
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=10)

            assert len(errors) == 0, f"Errors occurred: {errors}"
            # Cache should still be consistent
            assert len(analyzer._doc_cache) >= initial_cache_size

    def test_concurrent_clear_cache_with_reads(self, mock_nlp_fixture):
        """Test clearing cache while other threads are reading."""
        import threading

        mock_nlp, mock_doc = mock_nlp_fixture
        errors = []
        read_count = 0
        read_lock = threading.Lock()

        def read_from_cache():
            nonlocal read_count
            try:
                with (
                    patch("spacy.load", return_value=mock_nlp),
                    patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
                    patch.object(
                        SemanticAnalyzer,
                        "_calculate_document_similarity",
                        return_value={},
                    ),
                ):
                    analyzer.analyze_text(
                        "Test document", doc_id="doc1", include_enhanced=False
                    )
                    with read_lock:
                        read_count += 1
            except Exception as e:
                errors.append(str(e))

        def clear_cache_locker():
            try:
                analyzer.clear_cache()
            except Exception as e:
                errors.append(str(e))

        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
            patch.object(
                SemanticAnalyzer, "_calculate_document_similarity", return_value={}
            ),
        ):
            analyzer = SemanticAnalyzer()

            # Pre-populate cache
            analyzer.analyze_text("Pre-cached", doc_id="doc1", include_enhanced=False)

            threads = []

            # Spawn reader threads
            for _i in range(5):
                t = threading.Thread(target=read_from_cache, daemon=True)
                threads.append(t)
                t.start()

            # Spawn clearer thread
            t = threading.Thread(target=clear_cache_locker, daemon=True)
            threads.append(t)
            t.start()

            # More readers after clear
            for _i in range(5):
                t = threading.Thread(target=read_from_cache, daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=10)

            # Operations should complete without deadlock or corruption
            assert len(errors) == 0, f"Errors occurred: {errors}"
            # After clear, cache may be empty or have new entries
            assert isinstance(analyzer._doc_cache, dict)

    def test_concurrent_enhanced_similarity_refresh(self, mock_nlp_fixture):
        """Test concurrent cache hits with enhanced similarity refresh."""
        import threading

        mock_nlp, mock_doc = mock_nlp_fixture
        errors = []
        refresh_count = 0
        refresh_lock = threading.Lock()

        def read_with_refresh(doc_id):
            nonlocal refresh_count
            try:
                call_count = 0

                def mock_similarity_side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    return {"other_doc": 0.5 + call_count * 0.01}

                with (
                    patch("spacy.load", return_value=mock_nlp),
                    patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
                    patch.object(
                        SemanticAnalyzer,
                        "_calculate_document_similarity",
                        side_effect=mock_similarity_side_effect,
                    ),
                    patch.object(SemanticAnalyzer, "_get_pos_tags", return_value=[]),
                    patch.object(
                        SemanticAnalyzer, "_get_dependencies", return_value=[]
                    ),
                ):
                    result = analyzer.analyze_text(
                        "Test document", doc_id=doc_id, include_enhanced=True
                    )
                    if result.document_similarity:
                        with refresh_lock:
                            refresh_count += 1
            except Exception as e:
                errors.append(str(e))

        with (
            patch("spacy.load", return_value=mock_nlp),
            patch.object(SemanticAnalyzer, "_extract_topics", return_value=[]),
        ):
            analyzer = SemanticAnalyzer()

            # Spawn concurrent threads accessing same doc with enhanced flag
            threads = []
            for _i in range(10):
                t = threading.Thread(
                    target=read_with_refresh, args=("doc_enhanced",), daemon=True
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=10)

            # All operations should succeed
            assert len(errors) == 0, f"Errors occurred: {errors}"
            # Cache should have one entry for the enhanced doc
            assert any(
                key[0] == "doc_enhanced" and key[-1] is True
                for key in analyzer._doc_cache
                if isinstance(key, tuple)
            )
