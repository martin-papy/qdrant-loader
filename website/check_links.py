#!/usr/bin/env python3
"""
Link checker script to scan the website for dead links (404 errors).
"""

import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


class LinkChecker:
    def __init__(self, base_url="http://localhost:8000", max_depth=3):
        self.base_url = base_url.rstrip("/")
        self.max_depth = max_depth
        self.visited_urls = set()
        self.checked_links = set()
        self.dead_links = []
        self.broken_links = defaultdict(list)  # page -> [broken_links]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "QDrant-Loader-Link-Checker/1.0"})

    def is_internal_url(self, url):
        """Check if URL is internal to our site."""
        parsed = urlparse(url)
        base_parsed = urlparse(self.base_url)
        return parsed.netloc == base_parsed.netloc or not parsed.netloc

    def normalize_url(self, url):
        """Normalize URL for consistent checking."""
        # Remove fragment
        if "#" in url:
            url = url.split("#")[0]
        # Ensure trailing slash for directories
        if url.endswith("/index.html"):
            url = url[:-10]  # Remove index.html
        return url

    def extract_links_from_html(self, html_content, base_url):
        """Extract all links from HTML content."""
        links = set()

        # Find all href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        for match in re.finditer(href_pattern, html_content):
            link = match.group(1)
            if link.startswith("javascript:") or link.startswith("mailto:"):
                continue
            full_url = urljoin(base_url, link)
            links.add(self.normalize_url(full_url))

        # Find all src attributes (for images, scripts, etc.)
        src_pattern = r'src=["\']([^"\']+)["\']'
        for match in re.finditer(src_pattern, html_content):
            link = match.group(1)
            if link.startswith("data:"):
                continue
            full_url = urljoin(base_url, link)
            links.add(self.normalize_url(full_url))

        return links

    def check_url(self, url):
        """Check if a URL is accessible."""
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 405:  # Method not allowed, try GET
                response = self.session.get(url, timeout=10, allow_redirects=True)
            return response.status_code, response.reason
        except requests.exceptions.RequestException as e:
            return None, str(e)

    def crawl_page(self, url, depth=0):
        """Crawl a single page and extract links."""
        if depth > self.max_depth or url in self.visited_urls:
            return

        print(f"{'  ' * depth}Crawling: {url}")
        self.visited_urls.add(url)

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"{'  ' * depth}⚠️  Page returned {response.status_code}: {url}")
                return

            # Extract links from this page
            links = self.extract_links_from_html(response.text, url)

            # Check each link
            for link in links:
                if link not in self.checked_links:
                    self.checked_links.add(link)
                    status_code, reason = self.check_url(link)

                    if status_code is None or status_code >= 400:
                        self.dead_links.append(
                            {
                                "url": link,
                                "status": status_code,
                                "reason": reason,
                                "found_on": url,
                            }
                        )
                        self.broken_links[url].append(link)
                        print(
                            f"{'  ' * depth}❌ BROKEN: {link} ({status_code}: {reason})"
                        )
                    elif status_code >= 300:
                        print(f"{'  ' * depth}🔄 REDIRECT: {link} ({status_code})")
                    else:
                        print(f"{'  ' * depth}✅ OK: {link}")

                    # Small delay to be nice to the server
                    time.sleep(0.1)

                # Recursively crawl internal HTML pages
                if (
                    self.is_internal_url(link)
                    and depth < self.max_depth
                    and link not in self.visited_urls
                    and (
                        link.endswith(".html")
                        or link.endswith("/")
                        or "." not in Path(urlparse(link).path).name
                    )
                ):
                    self.crawl_page(link, depth + 1)

        except requests.exceptions.RequestException as e:
            print(f"{'  ' * depth}❌ ERROR crawling {url}: {e}")

    def run_check(self):
        """Run the complete link check."""
        print(f"🔍 Starting link check for {self.base_url}")
        print(f"📊 Max depth: {self.max_depth}")
        print("=" * 60)

        start_time = time.time()
        self.crawl_page(self.base_url)
        end_time = time.time()

        print("\n" + "=" * 60)
        print("📋 LINK CHECK SUMMARY")
        print("=" * 60)
        print(f"⏱️  Time taken: {end_time - start_time:.2f} seconds")
        print(f"🌐 Pages crawled: {len(self.visited_urls)}")
        print(f"🔗 Links checked: {len(self.checked_links)}")
        print(f"❌ Broken links found: {len(self.dead_links)}")

        if self.dead_links:
            print("\n💥 BROKEN LINKS DETAILS:")
            print("-" * 40)
            for link_info in self.dead_links:
                print(f"URL: {link_info['url']}")
                print(f"Status: {link_info['status']} - {link_info['reason']}")
                print(f"Found on: {link_info['found_on']}")
                print("-" * 40)

            print("\n📄 PAGES WITH BROKEN LINKS:")
            for page, broken_links in self.broken_links.items():
                print(f"\n{page}:")
                for link in broken_links:
                    print(f"  ❌ {link}")
        else:
            print("\n🎉 No broken links found! All links are working correctly.")

        return len(self.dead_links) == 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check website for broken links")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Base URL to check"
    )
    parser.add_argument("--depth", type=int, default=3, help="Maximum crawl depth")
    parser.add_argument(
        "--external", action="store_true", help="Also check external links"
    )

    args = parser.parse_args()

    checker = LinkChecker(args.url, args.depth)

    try:
        success = checker.run_check()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Link check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Link check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
