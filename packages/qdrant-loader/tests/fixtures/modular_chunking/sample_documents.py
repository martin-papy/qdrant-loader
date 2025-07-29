"""Test fixtures for modular chunking integration tests.

This module provides sample documents and content for testing the complete
modular chunking system without mocks.
"""

from datetime import UTC, datetime
from qdrant_loader.core.document import Document


def create_sample_text_document() -> Document:
    """Create a sample text document for testing."""
    content = """Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models. These models enable computers to perform specific tasks without explicit instructions, using patterns and inference instead.

Key Concepts

There are several fundamental concepts in machine learning:

1. Supervised Learning
Supervised learning uses labeled training data to learn a mapping function from input variables to output variables. Common examples include classification and regression problems.

2. Unsupervised Learning  
Unsupervised learning finds hidden patterns in data without labeled examples. Clustering and dimensionality reduction are typical applications.

3. Reinforcement Learning
Reinforcement learning involves an agent learning through interaction with an environment, receiving rewards or penalties for actions.

Applications

Machine learning has numerous practical applications:

- Image recognition and computer vision
- Natural language processing
- Recommendation systems  
- Fraud detection
- Autonomous vehicles
- Medical diagnosis

Challenges and Considerations

Despite its power, machine learning faces several challenges:

Data Quality: The quality of training data significantly impacts model performance. Poor quality data leads to poor models.

Bias and Fairness: Models can perpetuate or amplify existing biases present in training data.

Interpretability: Complex models like deep neural networks are often "black boxes" that are difficult to interpret.

Conclusion

Machine learning continues to evolve rapidly, with new techniques and applications emerging regularly. Understanding its fundamentals is crucial for anyone working with data and AI systems."""

    return Document(
        content=content,
        url="https://example.com/ml-intro.txt",
        content_type="txt",
        source_type="test",
        source="test_integration",
        title="Introduction to Machine Learning",
        metadata={
            "author": "Test Author",
            "file_name": "ml-intro.txt",
            "topic": "machine_learning",
            "word_count": len(content.split()),
            "source": "test_integration"
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


def create_formatted_text_document() -> Document:
    """Create a text document with various formatting for testing."""
    content = """# Technical Documentation

This document contains **various formatting** elements to test the parser's capabilities.

## Section 1: Lists and Formatting

Here's a bulleted list:
- First item with *italic text*
- Second item with **bold text**  
- Third item with `code snippets`

And a numbered list:
1. Primary point
2. Secondary point
3. Tertiary point

## Section 2: Code and Technical Content

Here's some sample code:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

Important variables:
- MAX_ITERATIONS = 1000
- DEFAULT_TIMEOUT = 30

## Section 3: References and Links

See Chapter 1 for background information.
Refer to Figure 2.1 for the visual representation.
Visit https://example.com for more details.

Contact: support@example.com for questions.

## Section 4: Mixed Content

This section has (parenthetical remarks) and [bracketed notes].

Mathematical concepts: E = mc² and ∑(x) for summation.

"Quoted text is important" - Author Name

IMPORTANT: This text is in ALL CAPS for emphasis."""

    return Document(
        content=content,
        url="https://example.com/formatted-doc.md",
        content_type="md",  # Even though it's testing text parsing
        source_type="test",
        source="test_integration",
        title="Technical Documentation",
        metadata={
            "author": "Technical Writer",
            "file_name": "formatted-doc.md",
            "topic": "documentation",
            "has_code": True,
            "has_formatting": True,
            "source": "test_integration"
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


def create_simple_text_document() -> Document:
    """Create a simple text document for basic testing."""
    content = """Simple Document

This is a straightforward document with minimal formatting.

It has a few paragraphs of regular text content.

The content is designed to test basic text processing without complex structures.

Each paragraph contains multiple sentences. The sentences vary in length and complexity. Some are short. Others provide more detailed information about the testing approach.

Final paragraph to complete the document."""

    return Document(
        content=content,
        url="https://example.com/simple.txt",
        content_type="txt",
        source_type="test",
        source="test_integration",
        title="Simple Document",
        metadata={
            "file_name": "simple.txt",
            "topic": "testing",
            "complexity": "low",
            "source": "test_integration"
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


def create_long_text_document() -> Document:
    """Create a long document to test chunking with multiple chunks."""
    # Create content that will definitely be split into multiple chunks
    paragraphs = []
    
    for i in range(20):
        paragraph = f"""Paragraph {i + 1}: This is a substantial paragraph that contains enough content to contribute meaningfully to the overall document length. Each paragraph discusses different aspects of the testing methodology and provides sufficient detail to ensure that the chunking algorithm will have realistic content to work with. The paragraph includes multiple sentences with varying complexity and length to simulate real-world document content patterns."""
        paragraphs.append(paragraph)
    
    content = "\n\n".join(paragraphs)
    
    return Document(
        content=content,
        url="https://example.com/long-document.txt",
        content_type="txt",
        source_type="test",
        source="test_integration",
        title="Long Test Document",
        metadata={
            "file_name": "long-document.txt",
            "topic": "testing",
            "complexity": "high",
            "paragraph_count": 20,
            "estimated_chunks": "multiple",
            "source": "test_integration"
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


def create_edge_case_document() -> Document:
    """Create a document with edge cases for testing robustness."""
    content = """Edge Case Testing

This document tests various edge cases:

Empty lines:



Multiple spaces:     lots     of     spaces

Unicode characters: café, naïve, résumé, 中文, العربية

Special characters: @#$%^&*()_+-={}[]|\\:";'<>?,./

Numbers and dates: 2024-01-15, $1,234.56, 42%

Very short line.

A

This is a line with mixed    indentation
        and varying        spacing patterns
    that might confuse parsers.

URLs and emails mixed: https://example.com and user@domain.org in same line.

CAPS LOCK TEXT MIXED with normal text AND numbers 123.

Final edge case: line ending without punctuation"""

    return Document(
        content=content,
        url="https://example.com/edge-cases.txt",
        content_type="txt",
        source_type="test",
        source="test_integration",
        title="Edge Case Document",
        metadata={
            "file_name": "edge-cases.txt",
            "topic": "testing",
            "complexity": "edge_cases",
            "has_unicode": True,
            "has_special_chars": True,
            "source": "test_integration"
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


# Export all fixture functions
__all__ = [
    "create_sample_text_document",
    "create_formatted_text_document", 
    "create_simple_text_document",
    "create_long_text_document",
    "create_edge_case_document"
] 