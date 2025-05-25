"""Tests for the TopicModeler class."""

import pytest
from qdrant_loader.core.text_processing.topic_modeler import TopicModeler


@pytest.fixture
def topic_modeler():
    """Create a TopicModeler instance for testing."""
    return TopicModeler(num_topics=2, passes=2)


def test_preprocess_text(topic_modeler):
    """Test text preprocessing."""
    text = "This is a test document. It contains some words and punctuation!"
    tokens = topic_modeler._preprocess_text(text)

    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert all(isinstance(token, str) for token in tokens)
    assert all(token.islower() for token in tokens)
    assert "this" in tokens
    assert "test" in tokens
    assert "document" in tokens
    assert "!" not in tokens  # Punctuation should be removed


def test_train_model(topic_modeler):
    """Test LDA model training."""
    texts = [
        "This is a test document about machine learning.",
        "Machine learning is a field of artificial intelligence.",
        "Artificial intelligence helps computers learn from data.",
        "Data analysis is important for machine learning.",
        "Learning algorithms process data to make predictions.",
    ]

    topic_modeler.train_model(texts)

    assert topic_modeler.dictionary is not None
    assert topic_modeler.lda_model is not None
    assert len(topic_modeler.dictionary) > 0


def test_infer_topics_without_training(topic_modeler):
    """Test topic inference without training."""
    result = topic_modeler.infer_topics("This is a test document.")

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    assert len(result["topics"]) == 0
    assert result["coherence"] == 0.0


def test_infer_topics_with_training(topic_modeler):
    """Test topic inference after training."""
    # Train the model
    texts = [
        "This is a test document about machine learning.",
        "Machine learning is a field of artificial intelligence.",
        "Artificial intelligence helps computers learn from data.",
        "Data analysis is important for machine learning.",
        "Learning algorithms process data to make predictions.",
    ]
    topic_modeler.train_model(texts)

    # Test inference
    result = topic_modeler.infer_topics(
        "Machine learning uses data to make predictions."
    )

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    assert len(result["topics"]) > 0
    assert isinstance(result["coherence"], float)


def test_empty_text_handling(topic_modeler):
    """Test handling of empty text."""
    # Train the model
    texts = ["This is a test document.", "Another test document."]
    topic_modeler.train_model(texts)

    # Test empty text
    result = topic_modeler.infer_topics("")

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    assert len(result["topics"]) == 0
    assert result["coherence"] == 0.0


def test_small_corpus_handling(topic_modeler):
    """Test handling of small corpus."""
    # Test with very small corpus
    texts = ["This is a test document."]
    topic_modeler.train_model(texts)

    result = topic_modeler.infer_topics("Another test document.")

    assert isinstance(result, dict)
    assert "topics" in result
    assert "coherence" in result
    # Even with small corpus, we should get some topics
    assert len(result["topics"]) > 0
