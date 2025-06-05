"""Test cases for Confluence chunking issue #27.

This module contains test cases that reproduce the issue where Confluence documents
always result in single chunks regardless of the chunking size specified in configuration.
"""

import pytest
from unittest.mock import Mock, patch

from qdrant_loader.config import GlobalConfig, Settings
from qdrant_loader.config.types import SourceType
from qdrant_loader.core.chunking.strategy.html_strategy import HTMLChunkingStrategy
from qdrant_loader.core.document import Document


class TestConfluenceChunkingIssue:
    """Test cases for reproducing and fixing Confluence chunking issue #27."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with small chunk size to reproduce the issue."""
        settings = Mock(spec=Settings)

        # Mock global_config
        global_config = Mock()

        # Mock chunking config
        chunking_config = Mock()
        chunking_config.chunk_size = 100  # Small chunk size as in the issue
        chunking_config.chunk_overlap = 20

        # Mock semantic analysis config
        semantic_analysis_config = Mock()
        semantic_analysis_config.num_topics = 5
        semantic_analysis_config.lda_passes = 1

        global_config.chunking = chunking_config
        global_config.semantic_analysis = semantic_analysis_config
        settings.global_config = global_config

        return settings

    @pytest.fixture
    def html_strategy(self, mock_settings):
        """Create an HTML chunking strategy instance."""
        with patch(
            "qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer"
        ):
            return HTMLChunkingStrategy(mock_settings)

    @pytest.fixture
    def confluence_html_single_div(self):
        """Typical Confluence HTML with all content in a single div - reproduces the issue."""
        return """
        <html>
        <head><title>Confluence Page</title></head>
        <body>
            <div class="wiki-content">
                <h1>Aegis - Capacity Planning Sprint 14</h1>
                <p>This is a comprehensive document about capacity planning for Sprint 14. 
                It contains detailed information about resource allocation, timeline planning, 
                and capacity management strategies. The document includes multiple sections 
                covering different aspects of the planning process including team capacity, 
                infrastructure requirements, and delivery milestones. This content should 
                definitely be split into multiple chunks when using a chunk size of 100 characters, 
                but currently it results in a single large chunk due to the semantic HTML 
                chunking strategy treating the entire wiki-content div as one semantic unit.</p>
                
                <h2>Resource Allocation</h2>
                <p>The resource allocation section provides detailed breakdown of team members, 
                their roles, and time commitments for the sprint. This includes both development 
                and testing resources, as well as infrastructure and support personnel.</p>
                
                <h2>Timeline Planning</h2>
                <p>Timeline planning involves creating detailed schedules for all sprint activities, 
                including development phases, testing cycles, and deployment windows. The timeline 
                must account for dependencies between different work streams and potential risks.</p>
                
                <ul>
                    <li>Development Phase 1: Week 1-2</li>
                    <li>Testing Phase: Week 2-3</li>
                    <li>Deployment: Week 4</li>
                    <li>Post-deployment monitoring: Week 4-5</li>
                </ul>
                
                <h2>Capacity Management</h2>
                <p>Capacity management ensures that we have adequate resources to meet sprint 
                commitments while maintaining quality standards. This involves monitoring team 
                velocity, identifying bottlenecks, and adjusting plans as needed.</p>
            </div>
        </body>
        </html>
        """

    @pytest.fixture
    def confluence_html_nested_structure(self):
        """Confluence HTML with nested semantic structure."""
        return """
        <html>
        <body>
            <div class="wiki-content">
                <article>
                    <section>
                        <h1>Project Overview</h1>
                        <p>This is a project overview section with substantial content that should be chunked appropriately.</p>
                    </section>
                    <section>
                        <h2>Technical Details</h2>
                        <p>Technical details section with implementation specifics and architectural decisions.</p>
                        <div class="code-block">
                            <pre>function example() { return "code sample"; }</pre>
                        </div>
                    </section>
                </article>
            </div>
        </body>
        </html>
        """

    @pytest.fixture
    def confluence_html_minimal(self):
        """Minimal Confluence HTML that should still be chunked properly."""
        return """
        <div class="wiki-content">
            <p>Short content that fits in one chunk but should still be processed correctly by the chunking strategy.</p>
        </div>
        """

    def test_reproduce_confluence_single_chunk_issue(
        self, html_strategy, mock_settings, confluence_html_single_div
    ):
        """Reproduce the issue: Confluence HTML results in single chunk despite small chunk_size."""
        # Use the HTML chunking strategy with small chunk size
        strategy = html_strategy

        # Create a Confluence document
        document = Document(
            title="Aegis - Capacity Planning Sprint 14",
            content=confluence_html_single_div,
            content_type="html",
            metadata={
                "id": "7539a4ba-2d29-7188-c58e-ef93a9f4ab67",
                "space": "engdocs",
                "type": "page",
            },
            source_type=SourceType.CONFLUENCE,
            source="engdocs",
            url="https://confluence.example.com/pages/123",
        )

        # Chunk the document
        chunks = strategy.chunk_document(document)

        # Current behavior (issue): Should result in 1 chunk despite chunk_size=100
        # Expected behavior (after fix): Should result in multiple chunks

        # Log the results for analysis
        total_content_length = len(confluence_html_single_div)
        chunk_count = len(chunks)
        avg_chunk_size = (
            sum(len(chunk.content) for chunk in chunks) / len(chunks) if chunks else 0
        )

        print(f"\n=== Confluence Chunking Test Results ===")
        print(f"Original content length: {total_content_length}")
        print(
            f"Configured chunk_size: {mock_settings.global_config.chunking.chunk_size}"
        )
        print(
            f"Configured chunk_overlap: {mock_settings.global_config.chunking.chunk_overlap}"
        )
        print(f"Resulting chunk count: {chunk_count}")
        print(f"Average chunk size: {avg_chunk_size:.1f}")
        print(f"Chunk sizes: {[len(chunk.content) for chunk in chunks]}")

        # This test documents the current problematic behavior
        # After implementing the fix, we should update this test to verify the correct behavior
        assert chunk_count >= 1, "Should produce at least one chunk"

        # Document the issue: with chunk_size=100, we expect multiple chunks but likely get 1
        if (
            chunk_count == 1
            and avg_chunk_size > mock_settings.global_config.chunking.chunk_size * 2
        ):
            print(
                f"⚠️  ISSUE REPRODUCED: Single chunk of {avg_chunk_size:.1f} chars with chunk_size={mock_settings.global_config.chunking.chunk_size}"
            )
            print("This confirms the reported issue in #27")

    def test_confluence_html_structure_analysis(
        self, html_strategy, confluence_html_single_div
    ):
        """Analyze how the HTML strategy processes Confluence HTML structure."""
        strategy = html_strategy

        # Test the internal _split_text method to understand the parsing
        sections = strategy._split_text(confluence_html_single_div)

        print(f"\n=== HTML Structure Analysis ===")
        print(f"Number of sections found: {len(sections)}")

        for i, section in enumerate(sections):
            print(f"\nSection {i+1}:")
            print(f"  Tag: {section.get('tag_name', 'unknown')}")
            print(f"  Type: {section.get('section_type', 'unknown')}")
            print(f"  Content length: {len(section.get('content', ''))}")
            print(f"  Text length: {len(section.get('text_content', ''))}")
            print(f"  Title: {section.get('title', 'No title')[:50]}...")

        # Analyze why we get single/few sections
        assert len(sections) >= 1, "Should find at least one section"

    def test_expected_chunking_behavior_after_fix(
        self, mock_settings, confluence_html_single_div
    ):
        """Test case for expected behavior after implementing the fix."""
        # This test defines what we want to achieve after fixing the issue

        # Calculate expected number of chunks based on content length and chunk_size
        # Remove HTML tags to get approximate text content length
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(confluence_html_single_div, "html.parser")
        text_content = soup.get_text(strip=True)
        text_length = len(text_content)

        chunk_size = mock_settings.global_config.chunking.chunk_size  # 100
        chunk_overlap = mock_settings.global_config.chunking.chunk_overlap  # 20

        # Rough calculation of expected chunks (accounting for overlap)
        effective_chunk_size = chunk_size - chunk_overlap
        expected_min_chunks = max(1, text_length // chunk_size)

        print(f"\n=== Expected Behavior Analysis ===")
        print(f"Text content length: {text_length}")
        print(f"Chunk size: {chunk_size}")
        print(f"Chunk overlap: {chunk_overlap}")
        print(f"Expected minimum chunks: {expected_min_chunks}")

        # TODO: After implementing the fix, update this test to verify actual chunking
        # For now, this documents our expectations

        # The fix should ensure that:
        # 1. Large semantic sections are split when they exceed chunk_size
        # 2. Chunk overlap is properly applied
        # 3. Semantic metadata is preserved in split chunks

        assert (
            expected_min_chunks > 1
        ), f"With {text_length} chars and chunk_size {chunk_size}, we should expect multiple chunks"

    def test_confluence_vs_regular_html_chunking(self, html_strategy):
        """Compare how Confluence HTML is chunked vs regular semantic HTML."""
        strategy = html_strategy

        # Regular semantic HTML with clear section boundaries
        regular_html = """
        <html>
        <body>
            <article>
                <h1>Title</h1>
                <p>First paragraph with some content.</p>
            </article>
            <section>
                <h2>Section 1</h2>
                <p>Section 1 content here.</p>
            </section>
            <section>
                <h2>Section 2</h2>
                <p>Section 2 content here.</p>
            </section>
        </body>
        </html>
        """

        # Confluence-style HTML (single container)
        confluence_html = """
        <html>
        <body>
            <div class="wiki-content">
                <h1>Title</h1>
                <p>First paragraph with some content.</p>
                <h2>Section 1</h2>
                <p>Section 1 content here.</p>
                <h2>Section 2</h2>
                <p>Section 2 content here.</p>
            </div>
        </body>
        </html>
        """

        regular_sections = strategy._split_text(regular_html)
        confluence_sections = strategy._split_text(confluence_html)

        print(f"\n=== HTML Structure Comparison ===")
        print(f"Regular HTML sections: {len(regular_sections)}")
        print(f"Confluence HTML sections: {len(confluence_sections)}")

        # This helps us understand why Confluence HTML behaves differently
        assert len(regular_sections) >= 1
        assert len(confluence_sections) >= 1

    def test_chunk_size_variations(self, mock_settings, confluence_html_single_div):
        """Test how different chunk sizes affect Confluence document chunking."""
        chunk_sizes = [50, 100, 200, 500, 1000]
        results = {}

        for chunk_size in chunk_sizes:
            # Update mock settings
            mock_settings.global_config.chunking.chunk_size = chunk_size

            with patch(
                "qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer"
            ):
                strategy = HTMLChunkingStrategy(mock_settings)
                document = Document(
                    title="Test Document",
                    content=confluence_html_single_div,
                    content_type="html",
                    metadata={},
                    source_type=SourceType.CONFLUENCE,
                    source="test",
                    url="https://test.com",
                )

                chunks = strategy.chunk_document(document)
                avg_size = (
                    sum(len(chunk.content) for chunk in chunks) / len(chunks)
                    if chunks
                    else 0
                )

                results[chunk_size] = {
                    "chunk_count": len(chunks),
                    "avg_chunk_size": avg_size,
                }

        print(f"\n=== Chunk Size Variation Analysis ===")
        for chunk_size, result in results.items():
            print(
                f"Chunk size {chunk_size}: {result['chunk_count']} chunks, avg size {result['avg_chunk_size']:.1f}"
            )

        # Document the current behavior across different chunk sizes
        for chunk_size, result in results.items():
            assert (
                result["chunk_count"] >= 1
            ), f"Should produce at least one chunk for size {chunk_size}"

    def test_confluence_html_edge_cases(self, html_strategy):
        """Test edge cases in Confluence HTML structure."""
        strategy = html_strategy

        # Empty wiki-content
        empty_html = '<div class="wiki-content"></div>'

        # Very large single paragraph
        large_paragraph = (
            f'<div class="wiki-content"><p>{"Very long content. " * 100}</p></div>'
        )

        # Nested divs (common in Confluence)
        nested_html = """
        <div class="wiki-content">
            <div class="content-wrapper">
                <div class="main-content">
                    <p>Nested content that should still be chunked properly.</p>
                </div>
            </div>
        </div>
        """

        test_cases = [
            ("empty", empty_html),
            ("large_paragraph", large_paragraph),
            ("nested", nested_html),
        ]

        print(f"\n=== Edge Cases Analysis ===")
        for name, html in test_cases:
            sections = strategy._split_text(html)
            print(f"{name}: {len(sections)} sections")

            if sections:
                total_length = sum(len(s.get("text_content", "")) for s in sections)
                print(f"  Total text length: {total_length}")

    @pytest.mark.parametrize(
        "chunk_size,expected_behavior",
        [
            (50, "Should produce many small chunks"),
            (100, "Should produce multiple medium chunks"),
            (500, "Should produce fewer larger chunks"),
            (2000, "Might produce single chunk if content is small"),
        ],
    )
    def test_chunk_size_expectations(
        self, mock_settings, confluence_html_single_div, chunk_size, expected_behavior
    ):
        """Parameterized test for different chunk size expectations."""
        mock_settings.global_config.chunking.chunk_size = chunk_size

        with patch(
            "qdrant_loader.core.text_processing.semantic_analyzer.SemanticAnalyzer"
        ):
            strategy = HTMLChunkingStrategy(mock_settings)
            document = Document(
                title="Test",
                content=confluence_html_single_div,
                content_type="html",
                metadata={},
                source_type=SourceType.CONFLUENCE,
                source="test",
                url="https://test.com",
            )

            chunks = strategy.chunk_document(document)

            print(
                f"\nChunk size {chunk_size}: {len(chunks)} chunks ({expected_behavior})"
            )

            # Basic validation
            assert len(chunks) >= 1

            # After fix implementation, add more specific assertions based on expected_behavior
