import unittest
from qdrant_loader.core.document import Document

class TestDocumentIdGeneration(unittest.TestCase):
    def setUp(self):
        self.test_cases = [
            # Basic cases
            {
                "source_type": "git",
                "source": "repo1",
                "url": "https://example.com/doc",
                "variations": [
                    {"source_type": "GIT", "source": "REPO1", "url": "HTTPS://EXAMPLE.COM/DOC/"},
                    {"source_type": " git ", "source": " repo1 ", "url": "https://example.com/doc?param1=value1"},
                ]
            },
            # URL variations
            {
                "source_type": "confluence",
                "source": "space1",
                "url": "https://wiki.example.com/page",
                "variations": [
                    {"url": "https://wiki.example.com/page/"},
                    {"url": "https://wiki.example.com/page?param2=value2&param1=value1"},
                    {"url": "https://wiki.example.com/page#section1"},
                ]
            },
            # Special characters
            {
                "source_type": "jira",
                "source": "project-1",
                "url": "https://jira.example.com/browse/PROJ-123",
                "variations": [
                    {"url": "https://jira.example.com/browse/PROJ-123/"},
                    {"source": "PROJECT-1", "url": "https://jira.example.com/browse/proj-123"},
                ]
            },
            # Complex URLs
            {
                "source_type": "publicdocs",
                "source": "docs-site",
                "url": "https://docs.example.com/v1/api/reference#authentication",
                "variations": [
                    {"url": "https://docs.example.com/v1/api/reference?version=1.0#authentication"},
                    {"url": "https://docs.example.com/v1/api/reference/?version=1.0&lang=en#authentication"},
                ]
            }
        ]

    def test_id_consistency(self):
        """Test that the same inputs always generate the same ID."""
        for test_case in self.test_cases:
            # Generate base ID
            base_id = Document.generate_id(
                test_case["source_type"],
                test_case["source"],
                test_case["url"]
            )
            
            # Test all variations
            for variation in test_case["variations"]:
                variation_id = Document.generate_id(
                    variation.get("source_type", test_case["source_type"]),
                    variation.get("source", test_case["source"]),
                    variation.get("url", test_case["url"])
                )
                self.assertEqual(
                    base_id,
                    variation_id,
                    f"IDs should be equal for variations of {test_case['url']}"
                )

    def test_id_uniqueness(self):
        """Test that different inputs generate different IDs."""
        # Test different source types
        id1 = Document.generate_id("git", "repo1", "https://example.com/doc")
        id2 = Document.generate_id("confluence", "repo1", "https://example.com/doc")
        self.assertNotEqual(id1, id2, "Different source types should generate different IDs")

        # Test different sources
        id1 = Document.generate_id("git", "repo1", "https://example.com/doc")
        id2 = Document.generate_id("git", "repo2", "https://example.com/doc")
        self.assertNotEqual(id1, id2, "Different sources should generate different IDs")

        # Test different URLs
        id1 = Document.generate_id("git", "repo1", "https://example.com/doc1")
        id2 = Document.generate_id("git", "repo1", "https://example.com/doc2")
        self.assertNotEqual(id1, id2, "Different URLs should generate different IDs")

    def test_id_format(self):
        """Test that generated IDs are valid UUIDs."""
        import uuid
        
        # Test multiple cases
        test_cases = [
            ("git", "repo1", "https://example.com/doc"),
            ("confluence", "space1", "https://wiki.example.com/page"),
            ("jira", "project-1", "https://jira.example.com/browse/PROJ-123"),
        ]
        
        for source_type, source, url in test_cases:
            doc_id = Document.generate_id(source_type, source, url)
            # Try to parse the ID as a UUID
            try:
                uuid.UUID(doc_id)
            except ValueError:
                self.fail(f"Generated ID '{doc_id}' is not a valid UUID")

if __name__ == '__main__':
    unittest.main() 