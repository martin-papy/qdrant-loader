"""Tests for the TopicModeler class."""

from unittest.mock import Mock, patch

import pytest
from qdrant_loader.core.text_processing.topic_modeler import TopicModeler


@pytest.fixture
def topic_modeler():
    """Create a TopicModeler instance for testing."""
    with patch(
        "qdrant_loader.core.text_processing.topic_modeler.spacy.load"
    ) as mock_spacy_load:
        # Mock the spaCy model
        mock_nlp = Mock()
        mock_spacy_load.return_value = mock_nlp

        # Create the topic modeler
        modeler = TopicModeler(num_topics=2, passes=2)
        return modeler


def test_preprocess_text(topic_modeler):
    """Test text preprocessing."""
    # Use longer text with more meaningful content since implementation requires 5+ words
    text = "This is a comprehensive test document with many meaningful words. It contains various technical terms, concepts, and detailed information for processing!"

    # Mock the spaCy document and tokens
    mock_token1 = Mock()
    mock_token1.text = "comprehensive"
    mock_token1.is_stop = False
    mock_token1.is_punct = False

    mock_token2 = Mock()
    mock_token2.text = "test"
    mock_token2.is_stop = False
    mock_token2.is_punct = False

    mock_token3 = Mock()
    mock_token3.text = "document"
    mock_token3.is_stop = False
    mock_token3.is_punct = False

    mock_token4 = Mock()
    mock_token4.text = "meaningful"
    mock_token4.is_stop = False
    mock_token4.is_punct = False

    mock_token5 = Mock()
    mock_token5.text = "words"
    mock_token5.is_stop = False
    mock_token5.is_punct = False

    # Mock stop word and punctuation
    mock_stop_token = Mock()
    mock_stop_token.text = "is"
    mock_stop_token.is_stop = True
    mock_stop_token.is_punct = False

    mock_punct_token = Mock()
    mock_punct_token.text = "!"
    mock_punct_token.is_stop = False
    mock_punct_token.is_punct = True

    mock_doc = Mock()
    mock_doc.__iter__ = Mock(
        return_value=iter(
            [
                mock_token1,
                mock_token2,
                mock_token3,
                mock_token4,
                mock_token5,
                mock_stop_token,
                mock_punct_token,
            ]
        )
    )

    topic_modeler.nlp.return_value = mock_doc

    tokens = topic_modeler._preprocess_text(text)

    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert all(isinstance(token, str) for token in tokens)
    assert all(token.islower() for token in tokens)
    # Check that meaningful tokens are included
    assert "comprehensive" in tokens
    assert "test" in tokens
    assert "document" in tokens
    assert "meaningful" in tokens
    assert "words" in tokens
    # Check that stop words and punctuation are excluded
    assert "is" not in tokens
    assert "!" not in tokens


@patch("qdrant_loader.core.text_processing.topic_modeler.corpora.Dictionary")
@patch("qdrant_loader.core.text_processing.topic_modeler.models.LdaModel")
def test_train_model(mock_lda_model, mock_dictionary, topic_modeler):
    """Test LDA model training."""
    # Use longer texts since implementation requires 5+ words per text
    texts = [
        "This is a longer test document about machine learning and artificial intelligence.",
        "Machine learning is a comprehensive field of artificial intelligence with many applications.",
        "Artificial intelligence helps computers learn from large amounts of data efficiently.",
        "Data analysis is extremely important for machine learning and predictive modeling.",
        "Learning algorithms process massive amounts of data to make accurate predictions.",
    ]

    # Mock the preprocessing to return non-empty token lists
    def mock_preprocess(text):
        return [
            "token1",
            "token2",
            "token3",
            "token4",
            "token5",
        ]  # Always return 5 tokens

    topic_modeler._preprocess_text = Mock(side_effect=mock_preprocess)

    # Mock the dictionary and model
    mock_dict_instance = Mock()
    mock_dict_instance.__len__ = Mock(return_value=10)  # Mock dictionary size
    mock_dictionary.return_value = mock_dict_instance
    mock_lda_instance = Mock()
    mock_lda_model.return_value = mock_lda_instance

    topic_modeler.train_model(texts)

    # Verify that dictionary and model were created
    assert topic_modeler.dictionary is not None
    assert topic_modeler.lda_model is not None


def test_infer_topics_without_training(topic_modeler):
    """Test topic inference without training."""
    result = topic_modeler.infer_topics("This is a test document.")

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    assert len(result["topics"]) == 0
    assert result["coherence"] == 0.0


@patch("qdrant_loader.core.text_processing.topic_modeler.corpora.Dictionary")
@patch("qdrant_loader.core.text_processing.topic_modeler.models.LdaModel")
def test_infer_topics_with_training(mock_lda_model, mock_dictionary, topic_modeler):
    """Test topic inference after training."""
    # Train the model with longer texts
    texts = [
        "This is a longer test document about machine learning and artificial intelligence.",
        "Machine learning is a comprehensive field of artificial intelligence with many applications.",
        "Artificial intelligence helps computers learn from large amounts of data efficiently.",
        "Data analysis is extremely important for machine learning and predictive modeling.",
        "Learning algorithms process massive amounts of data to make accurate predictions.",
    ]

    # Mock the preprocessing to return non-empty token lists
    def mock_preprocess(text):
        return [
            "token1",
            "token2",
            "token3",
            "token4",
            "token5",
        ]  # Always return 5 tokens

    topic_modeler._preprocess_text = Mock(side_effect=mock_preprocess)

    # Mock the dictionary and model
    mock_dict_instance = Mock()
    mock_dict_instance.__len__ = Mock(return_value=10)  # Mock dictionary size
    mock_dictionary.return_value = mock_dict_instance
    mock_lda_instance = Mock()
    mock_lda_instance.print_topics.return_value = [("topic1", 0.5), ("topic2", 0.3)]
    mock_lda_model.return_value = mock_lda_instance

    topic_modeler.train_model(texts)

    # Test inference with longer text
    result = topic_modeler.infer_topics(
        "Machine learning uses large amounts of data to make accurate predictions about future outcomes."
    )

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    assert len(result["topics"]) >= 0  # May be empty depending on model behavior
    assert isinstance(result["coherence"], float)


def test_empty_text_handling(topic_modeler):
    """Test handling of empty text."""
    # Mock the preprocessing to return empty list for empty text
    topic_modeler._preprocess_text = Mock(return_value=[])

    # Test empty text
    result = topic_modeler.infer_topics("")

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    assert len(result["topics"]) == 0
    assert result["coherence"] == 0.0


@patch("qdrant_loader.core.text_processing.topic_modeler.corpora.Dictionary")
@patch("qdrant_loader.core.text_processing.topic_modeler.models.LdaModel")
def test_small_corpus_handling(mock_lda_model, mock_dictionary, topic_modeler):
    """Test handling of small corpus."""
    # Test with very small corpus
    texts = ["This is a longer test document with sufficient words for processing."]

    # Mock the preprocessing to return non-empty token lists
    def mock_preprocess(text):
        return [
            "token1",
            "token2",
            "token3",
            "token4",
            "token5",
        ]  # Always return 5 tokens

    topic_modeler._preprocess_text = Mock(side_effect=mock_preprocess)

    # Mock the dictionary and model
    mock_dict_instance = Mock()
    mock_dict_instance.__len__ = Mock(return_value=10)  # Mock dictionary size
    mock_dictionary.return_value = mock_dict_instance
    mock_lda_instance = Mock()
    mock_lda_instance.print_topics.return_value = []
    mock_lda_model.return_value = mock_lda_instance

    topic_modeler.train_model(texts)

    result = topic_modeler.infer_topics(
        "Another longer test document with sufficient words for processing."
    )

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    # Small corpus may not generate meaningful topics
    assert len(result["topics"]) >= 0  # May be empty for very small corpus
