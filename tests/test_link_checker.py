#!/usr/bin/env python3
"""
Tests for the link checker script.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
import responses

# Add website directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from website.check_links import LinkChecker


class TestLinkChecker:
    """Test cases for the LinkChecker class."""

    def test_init(self):
        """Test LinkChecker initialization."""
        checker = LinkChecker("http://example.com", max_depth=2)
        assert checker.base_url == "http://example.com"
        assert checker.max_depth == 2
        assert checker.visited_urls == set()
        assert checker.checked_links == set()
        assert checker.dead_links == []
        assert len(checker.broken_links) == 0
        assert isinstance(checker.session, requests.Session)

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        checker = LinkChecker("http://example.com/")
        assert checker.base_url == "http://example.com"

    def test_is_internal_url(self):
        """Test internal URL detection."""
        checker = LinkChecker("http://example.com")

        # Internal URLs
        assert checker.is_internal_url("http://example.com/page")
        assert checker.is_internal_url("/relative/path")
        assert checker.is_internal_url("relative/path")
        assert checker.is_internal_url("#fragment")

        # External URLs
        assert not checker.is_internal_url("http://other.com/page")
        assert not checker.is_internal_url("https://external.site")

    def test_normalize_url(self):
        """Test URL normalization."""
        checker = LinkChecker("http://example.com")

        # Remove fragments
        assert (
            checker.normalize_url("http://example.com/page#section")
            == "http://example.com/page"
        )

        # Remove index.html from directories
        assert (
            checker.normalize_url("http://example.com/docs/index.html")
            == "http://example.com/docs/"
        )

        # Keep regular files
        assert (
            checker.normalize_url("http://example.com/page.html")
            == "http://example.com/page.html"
        )

    def test_extract_links_from_html(self):
        """Test link extraction from HTML content."""
        checker = LinkChecker("http://example.com")

        html_content = """
        <html>
            <head>
                <link rel="stylesheet" href="/styles.css">
            </head>
            <body>
                <a href="/page1.html">Page 1</a>
                <a href="http://external.com">External</a>
                <a href="mailto:test@example.com">Email</a>
                <a href="javascript:void(0)">JS Link</a>
                <img src="/image.jpg" alt="Image">
                <script src="/script.js"></script>
                <img src="data:image/png;base64,abc123" alt="Data URL">
            </body>
        </html>
        """

        links = checker.extract_links_from_html(html_content, "http://example.com")

        expected_links = {
            "http://example.com/page1.html",
            "http://external.com",
            "http://example.com/image.jpg",
            "http://example.com/script.js",
            "http://example.com/styles.css",
        }

        assert links == expected_links

    @responses.activate
    def test_check_url_success(self):
        """Test successful URL checking."""
        checker = LinkChecker("http://example.com")

        responses.add(responses.HEAD, "http://example.com/page", status=200)

        status_code, reason = checker.check_url("http://example.com/page")
        assert status_code == 200
        assert reason == "OK"

    @responses.activate
    def test_check_url_method_not_allowed_fallback(self):
        """Test fallback to GET when HEAD returns 405."""
        checker = LinkChecker("http://example.com")

        responses.add(responses.HEAD, "http://example.com/page", status=405)
        responses.add(responses.GET, "http://example.com/page", status=200)

        status_code, reason = checker.check_url("http://example.com/page")
        assert status_code == 200

    @responses.activate
    def test_check_url_not_found(self):
        """Test URL checking for 404 errors."""
        checker = LinkChecker("http://example.com")

        responses.add(responses.HEAD, "http://example.com/missing", status=404)

        status_code, reason = checker.check_url("http://example.com/missing")
        assert status_code == 404
        assert reason == "Not Found"

    def test_check_url_connection_error(self):
        """Test URL checking with connection errors."""
        checker = LinkChecker("http://example.com")

        # Mock a connection error
        with patch.object(
            checker.session,
            "head",
            side_effect=requests.exceptions.ConnectionError("Connection failed"),
        ):
            status_code, reason = checker.check_url("http://example.com/page")
            assert status_code is None
            assert "Connection failed" in reason

    @responses.activate
    def test_crawl_page_basic(self):
        """Test basic page crawling."""
        checker = LinkChecker("http://example.com")

        html_content = """
        <html>
            <body>
                <a href="/page2.html">Page 2</a>
                <a href="http://external.com">External</a>
            </body>
        </html>
        """

        responses.add(
            responses.GET, "http://example.com/", body=html_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/page2.html", status=200)
        responses.add(responses.HEAD, "http://external.com", status=200)

        checker.crawl_page("http://example.com/")

        assert "http://example.com/" in checker.visited_urls
        assert "http://example.com/page2.html" in checker.checked_links
        assert "http://external.com" in checker.checked_links
        assert len(checker.dead_links) == 0

    @responses.activate
    def test_crawl_page_with_broken_links(self):
        """Test crawling page with broken links."""
        checker = LinkChecker("http://example.com")

        html_content = """
        <html>
            <body>
                <a href="/working.html">Working</a>
                <a href="/broken.html">Broken</a>
            </body>
        </html>
        """

        responses.add(
            responses.GET, "http://example.com/", body=html_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/working.html", status=200)
        responses.add(responses.HEAD, "http://example.com/broken.html", status=404)

        checker.crawl_page("http://example.com/")

        assert len(checker.dead_links) == 1
        assert checker.dead_links[0]["url"] == "http://example.com/broken.html"
        assert checker.dead_links[0]["status"] == 404
        assert checker.dead_links[0]["found_on"] == "http://example.com/"

    @responses.activate
    def test_crawl_page_max_depth(self):
        """Test that crawling respects max depth."""
        checker = LinkChecker("http://example.com", max_depth=1)

        # Page 1 content
        page1_content = '<a href="/page2.html">Page 2</a>'
        responses.add(
            responses.GET, "http://example.com/", body=page1_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/page2.html", status=200)

        # Page 2 content (should not be crawled due to depth limit)
        page2_content = '<a href="/page3.html">Page 3</a>'
        responses.add(
            responses.GET,
            "http://example.com/page2.html",
            body=page2_content,
            status=200,
        )
        responses.add(responses.HEAD, "http://example.com/page3.html", status=200)

        checker.crawl_page("http://example.com/")

        # Should visit page1 and page2, but not page3
        assert "http://example.com/" in checker.visited_urls
        assert "http://example.com/page2.html" in checker.visited_urls
        assert len(checker.visited_urls) == 2

    @responses.activate
    def test_crawl_page_avoids_duplicates(self):
        """Test that crawling avoids visiting the same page twice."""
        checker = LinkChecker("http://example.com")

        html_content = '<a href="/">Home</a>'
        responses.add(
            responses.GET, "http://example.com/", body=html_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/", status=200)

        # Crawl the same page twice
        checker.crawl_page("http://example.com/")
        initial_visit_count = len(checker.visited_urls)

        checker.crawl_page("http://example.com/")
        final_visit_count = len(checker.visited_urls)

        assert initial_visit_count == final_visit_count == 1

    @responses.activate
    def test_crawl_page_handles_non_200_response(self):
        """Test crawling handles non-200 responses gracefully."""
        checker = LinkChecker("http://example.com")

        responses.add(responses.GET, "http://example.com/", status=500)

        checker.crawl_page("http://example.com/")

        assert "http://example.com/" in checker.visited_urls
        assert len(checker.checked_links) == 0  # No links to check if page failed

    def test_crawl_page_handles_request_exception(self):
        """Test crawling handles request exceptions gracefully."""
        checker = LinkChecker("http://example.com")

        with patch.object(
            checker.session,
            "get",
            side_effect=requests.exceptions.RequestException("Network error"),
        ):
            checker.crawl_page("http://example.com/")

            assert "http://example.com/" in checker.visited_urls
            assert len(checker.checked_links) == 0

    @responses.activate
    def test_run_check_success(self):
        """Test complete link check run with no broken links."""
        checker = LinkChecker("http://example.com", max_depth=1)

        html_content = '<a href="/page.html">Page</a>'
        responses.add(
            responses.GET, "http://example.com", body=html_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/page.html", status=200)

        success = checker.run_check()

        assert success is True
        assert len(checker.dead_links) == 0

    @responses.activate
    def test_run_check_with_broken_links(self):
        """Test complete link check run with broken links."""
        checker = LinkChecker("http://example.com", max_depth=1)

        html_content = '<a href="/broken.html">Broken</a>'
        responses.add(
            responses.GET, "http://example.com", body=html_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/broken.html", status=404)

        success = checker.run_check()

        assert success is False
        assert len(checker.dead_links) == 1

    @responses.activate
    def test_redirects_handling(self):
        """Test handling of redirect responses."""
        checker = LinkChecker("http://example.com")

        html_content = '<a href="/redirect">Redirect</a>'
        responses.add(
            responses.GET, "http://example.com/", body=html_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/redirect", status=301)

        checker.crawl_page("http://example.com/")

        # Redirects should not be considered broken
        assert len(checker.dead_links) == 0

    def test_link_extraction_edge_cases(self):
        """Test link extraction with edge cases."""
        checker = LinkChecker("http://example.com")

        html_content = """
        <html>
            <body>
                <a href="">Empty href</a>
                <a href="#fragment-only">Fragment only</a>
                <a href="   /spaced.html   ">Spaced URL</a>
                <img src="">Empty src</a>
            </body>
        </html>
        """

        links = checker.extract_links_from_html(html_content, "http://example.com")

        # Should handle edge cases gracefully
        assert isinstance(links, set)

    @responses.activate
    def test_timeout_handling(self):
        """Test handling of request timeouts."""
        checker = LinkChecker("http://example.com")

        with patch.object(
            checker.session,
            "head",
            side_effect=requests.exceptions.Timeout("Request timed out"),
        ):
            status_code, reason = checker.check_url("http://example.com/slow")

            assert status_code is None
            assert "Request timed out" in reason


class TestLinkCheckerIntegration:
    """Integration tests for the link checker."""

    @responses.activate
    def test_full_website_crawl_simulation(self):
        """Test crawling a simulated website structure."""
        checker = LinkChecker("http://example.com", max_depth=2)

        # Home page
        home_content = """
        <html>
            <body>
                <a href="/docs/">Documentation</a>
                <a href="/about.html">About</a>
                <img src="/logo.png" alt="Logo">
            </body>
        </html>
        """

        # Docs index page
        docs_content = """
        <html>
            <body>
                <a href="/docs/guide.html">Guide</a>
                <a href="/docs/api.html">API</a>
                <a href="/">Home</a>
            </body>
        </html>
        """

        # Set up responses
        responses.add(
            responses.GET, "http://example.com", body=home_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/docs/", status=200)
        responses.add(responses.HEAD, "http://example.com/about.html", status=200)
        responses.add(responses.HEAD, "http://example.com/logo.png", status=200)

        responses.add(
            responses.GET, "http://example.com/docs/", body=docs_content, status=200
        )
        responses.add(responses.HEAD, "http://example.com/docs/guide.html", status=200)
        responses.add(
            responses.HEAD, "http://example.com/docs/api.html", status=404
        )  # Broken link
        responses.add(responses.HEAD, "http://example.com/", status=200)

        success = checker.run_check()

        assert success is False  # Should fail due to broken link
        assert len(checker.dead_links) == 1
        assert checker.dead_links[0]["url"] == "http://example.com/docs/api.html"
        assert checker.dead_links[0]["status"] == 404
        assert len(checker.visited_urls) >= 2  # At least home and docs pages

    @responses.activate
    def test_external_link_checking(self):
        """Test checking external links."""
        checker = LinkChecker("http://example.com")

        html_content = """
        <html>
            <body>
                <a href="https://github.com/user/repo">GitHub</a>
                <a href="https://broken-external.com">Broken External</a>
            </body>
        </html>
        """

        responses.add(
            responses.GET, "http://example.com", body=html_content, status=200
        )
        responses.add(responses.HEAD, "https://github.com/user/repo", status=200)
        responses.add(responses.HEAD, "https://broken-external.com", status=404)

        checker.crawl_page("http://example.com")

        assert len(checker.dead_links) == 1
        assert checker.dead_links[0]["url"] == "https://broken-external.com"


class TestLinkCheckerCLI:
    """Test the command-line interface."""

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        from website.check_links import main

        assert callable(main)

    @patch("sys.argv", ["check_links.py", "--url", "http://test.com", "--depth", "2"])
    def test_cli_argument_parsing(self):
        """Test CLI argument parsing."""
        import website.check_links as check_links

        mock_checker = Mock()
        mock_checker.run_check.return_value = True

        with patch("website.check_links.LinkChecker", return_value=mock_checker):
            with patch("sys.exit") as mock_exit:
                check_links.main()

        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["check_links.py"])
    def test_cli_default_arguments(self):
        """Test CLI with default arguments."""
        import website.check_links as check_links

        mock_checker = Mock()
        mock_checker.run_check.return_value = True

        with patch(
            "website.check_links.LinkChecker", return_value=mock_checker
        ) as mock_checker_class:
            with patch("sys.exit") as mock_exit:
                check_links.main()

        mock_checker_class.assert_called_once_with("http://127.0.0.1:3000/website/site", 3)
        mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["check_links.py"])
    def test_cli_with_broken_links(self):
        """Test CLI when broken links are found."""
        import website.check_links as check_links

        mock_checker = Mock()
        mock_checker.run_check.return_value = False  # Broken links found

        with patch("website.check_links.LinkChecker", return_value=mock_checker):
            with patch("sys.exit") as mock_exit:
                check_links.main()

        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["check_links.py"])
    def test_cli_keyboard_interrupt(self):
        """Test CLI handling of keyboard interrupt."""
        import website.check_links as check_links

        mock_checker = Mock()
        mock_checker.run_check.side_effect = KeyboardInterrupt()

        with patch("website.check_links.LinkChecker", return_value=mock_checker):
            with patch("sys.exit") as mock_exit:
                check_links.main()

        mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["check_links.py"])
    def test_cli_exception_handling(self):
        """Test CLI handling of general exceptions."""
        import website.check_links as check_links

        mock_checker = Mock()
        mock_checker.run_check.side_effect = Exception("Test error")

        with patch("website.check_links.LinkChecker", return_value=mock_checker):
            with patch("sys.exit") as mock_exit:
                check_links.main()

        mock_exit.assert_called_once_with(1)


@pytest.fixture
def sample_html():
    """Fixture providing sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Test Page</title>
            <link rel="stylesheet" href="/styles.css">
        </head>
        <body>
            <nav>
                <a href="/">Home</a>
                <a href="/docs/">Documentation</a>
                <a href="/about.html">About</a>
            </nav>
            <main>
                <h1>Welcome</h1>
                <p>This is a <a href="/test.html">test page</a>.</p>
                <img src="/images/logo.png" alt="Logo">
                <a href="https://external.com">External Link</a>
                <a href="mailto:test@example.com">Contact</a>
                <a href="javascript:void(0)">JS Link</a>
            </main>
            <script src="/js/app.js"></script>
        </body>
    </html>
    """


class TestLinkCheckerWithFixtures:
    """Tests using fixtures for more realistic scenarios."""

    def test_extract_links_from_realistic_html(self, sample_html):
        """Test link extraction from realistic HTML."""
        checker = LinkChecker("http://example.com")

        links = checker.extract_links_from_html(sample_html, "http://example.com")

        expected_links = {
            "http://example.com/",
            "http://example.com/docs/",
            "http://example.com/about.html",
            "http://example.com/test.html",
            "http://example.com/images/logo.png",
            "https://external.com",
            "http://example.com/styles.css",
            "http://example.com/js/app.js",
        }

        assert links == expected_links

    @responses.activate
    def test_crawl_realistic_page(self, sample_html):
        """Test crawling a realistic page structure."""
        checker = LinkChecker("http://example.com", max_depth=1)

        # Set up responses for all links
        responses.add(
            responses.GET, "http://example.com/", body=sample_html, status=200
        )
        responses.add(responses.HEAD, "http://example.com/", status=200)
        responses.add(responses.HEAD, "http://example.com/docs/", status=200)
        responses.add(responses.HEAD, "http://example.com/about.html", status=200)
        responses.add(
            responses.HEAD, "http://example.com/test.html", status=404
        )  # Broken
        responses.add(responses.HEAD, "http://example.com/images/logo.png", status=200)
        responses.add(responses.HEAD, "https://external.com", status=200)
        responses.add(responses.HEAD, "http://example.com/styles.css", status=200)
        responses.add(responses.HEAD, "http://example.com/js/app.js", status=200)

        checker.crawl_page("http://example.com/")

        assert len(checker.dead_links) == 1
        assert checker.dead_links[0]["url"] == "http://example.com/test.html"
        assert checker.dead_links[0]["status"] == 404
