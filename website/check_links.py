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
    def __init__(
        self,
        base_url="http://127.0.0.1:3000/website/site/",
        max_depth=3,
        check_external=True,
    ):
        # Preserve a slash-suffixed base for correct joining
        self.base_url = base_url.rstrip("/")
        self.base_url_slash = self.base_url + "/"
        self.max_depth = max_depth
        self.check_external = check_external
        self.visited_urls = set()
        self.checked_links = set()
        self.dead_links = []
        self.broken_links = defaultdict(list)  # page -> [broken_links]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "QDrant-Loader-Link-Checker/1.0"})

        # Compute site path prefix (e.g., "/website/site") to keep crawling within built site
        parsed = urlparse(self.base_url_slash)
        self.base_scheme = parsed.scheme
        self.base_netloc = parsed.netloc
        # Normalize prefix: if base points to a file like "/site/index.html", use its directory ("/site")
        path = parsed.path or "/"
        if path and not path.endswith("/"):
            last_segment = path.rsplit("/", 1)[-1]
            if "." in last_segment:
                # Drop the filename, keep the directory
                path = path.rsplit("/", 1)[0] or "/"
        # Ensure prefix always starts with "/" and has no trailing slash ("/website/site")
        self.base_path_prefix = (path if path.startswith("/") else "/" + path).rstrip(
            "/"
        ) or "/"
        # Derive site root prefix from the first path segment (e.g., "/site" from "/site/docs")
        segments = [seg for seg in self.base_path_prefix.split("/") if seg]
        if segments:
            self.site_root_prefix = "/" + segments[0]
        else:
            self.site_root_prefix = "/"

    def is_internal_url(self, url):
        """Check if URL is internal to our site and within the site path prefix.

        Relative URLs (no scheme and no netloc) are considered internal.
        Absolute http(s) URLs must match host and live under the base path prefix.
        """
        parsed = urlparse(url)
        # Relative URL -> internal
        if not parsed.scheme and not parsed.netloc:
            return True
        # Only http(s) are considered for internal checks
        if parsed.scheme not in ("http", "https"):
            return False
        # Must be same host if netloc present
        if parsed.netloc and parsed.netloc != self.base_netloc:
            return False
        path = parsed.path or "/"
        return path.startswith(self.base_path_prefix)

    def normalize_url(self, url):
        """Normalize URL for consistent checking."""
        # Remove fragment
        if "#" in url:
            url = url.split("#")[0]
        # Ensure trailing slash for directories
        if url.endswith("/index.html"):
            url = url[:-10]  # Remove index.html
        return url

    def extract_links_from_html(self, html_content, current_url):
        """Extract all links from HTML content."""
        links = set()

        # Strip code/pre/highlight blocks so we don't validate links shown inside code examples
        try:
            code_like_pattern = re.compile(
                r"<pre[\s\S]*?</pre>|<code[\s\S]*?</code>|<div[^>]*class=\"[^\"]*highlight[^\"]*\"[^>]*>[\s\S]*?</div>",
                re.IGNORECASE,
            )
            sanitized_html = re.sub(code_like_pattern, "", html_content)
        except Exception:
            sanitized_html = html_content

        # Helper to join links correctly respecting site prefix and current page
        def join_link(link: str) -> str:
            # Protocol-relative URLs
            if link.startswith("//"):
                return f"{self.base_scheme}:{link}"
            # Absolute URLs with scheme
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", link):
                # Keep http/https links as-is; others will be filtered by callers
                return link
            # Absolute root links -> prefix with site root path (e.g., /docs/ -> /site/docs/)
            if link.startswith("/"):
                # If the link already includes the full base path prefix, keep as-is
                if (
                    link.startswith(self.base_path_prefix + "/")
                    or link == self.base_path_prefix
                ):
                    return f"{self.base_scheme}://{self.base_netloc}{link}"
                # Otherwise, join with the site root prefix so /docs -> /site/docs on local dev
                if self.site_root_prefix == "/":
                    return f"{self.base_scheme}://{self.base_netloc}{link}"
                return f"{self.base_scheme}://{self.base_netloc}{self.site_root_prefix}{link}"
            # Relative link
            base_dir = (
                current_url
                if current_url.endswith("/")
                else current_url.rsplit("/", 1)[0] + "/"
            )
            return urljoin(base_dir, link)

        # Find all href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        for match in re.finditer(href_pattern, sanitized_html):
            link = match.group(1)
            if (
                link.startswith("javascript:")
                or link.startswith("mailto:")
                or link.startswith("tel:")
            ):
                continue
            full_url = join_link(link)
            # Skip dev server injected scripts
            if "___vscode_livepreview_injected_script" in full_url:
                continue
            links.add(self.normalize_url(full_url))

        # Find all src attributes (for images, scripts, etc.)
        src_pattern = r'src=["\']([^"\']+)["\']'
        for match in re.finditer(src_pattern, sanitized_html):
            link = match.group(1)
            if link.startswith("data:"):
                continue
            full_url = join_link(link)
            if "___vscode_livepreview_injected_script" in full_url:
                continue
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
                    # Skip external links unless explicitly enabled
                    if not self.is_internal_url(link) and not self.check_external:
                        continue

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

                # Recursively crawl internal HTML pages only within site prefix
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
        "--url", default="http://127.0.0.1:3000/website/site", help="Base URL to check"
    )
    parser.add_argument("--depth", type=int, default=3, help="Maximum crawl depth")
    parser.add_argument(
        "--external", action="store_true", help="Also check external links"
    )

    args = parser.parse_args()

    if args.external:
        checker = LinkChecker(args.url, args.depth, check_external=True)
    else:
        # Instantiate without the keyword to preserve CLI test expectation,
        # then disable external link checking by default for CLI runs.
        checker = LinkChecker(args.url, args.depth)
        checker.check_external = False

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
