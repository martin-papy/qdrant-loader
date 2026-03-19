#!/usr/bin/env python3
"""
Development Server - Watch mode with auto-rebuild and live reload.

Watches for changes in markdown and template files, automatically rebuilds
the website, and serves it locally with live reload capability.

Usage:
    python website/dev_server.py
    python website/dev_server.py --port 8000 --rebuild-delay 1
"""

import argparse
import http.server
import socketserver
import threading
import time
from pathlib import Path
from typing import Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    print("⚠️  watchdog not installed. Using fallback file monitoring.")
    print("   Install: pip install watchdog")
    print()

try:
    from .builder.core import WebsiteBuilder
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from builder.core import WebsiteBuilder


# ANSI colors for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RED = "\033[91m"


class LiveReloadHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with live reload script injection."""

    # Class variables shared across requests
    output_directory = Path("site")
    reload_version = 0

    def _live_reload_script(self) -> str:
        """Return script tags for the browser-side hot reload client."""
        return (
            f"<script>window.__qdrantHotReloadVersion={self.reload_version};</script>"
            '<script src="/assets/js/hot-reload.js"></script>'
        )

    def end_headers(self):
        """Inject live reload script before closing headers."""
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super().end_headers()

    def do_GET(self):
        """Override GET to inject live reload script into HTML."""
        if self.path.split("?")[0] == "/__reload":
            payload = str(self.reload_version).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", len(payload))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(payload)
            return

        # Build full file path
        url_path = self.path.split("?")[0].split("#")[0]  # Remove query/fragment
        if url_path.endswith("/"):
            file_path = self.output_directory / url_path.lstrip("/") / "index.html"
        else:
            file_path = self.output_directory / url_path.lstrip("/")

        # If it's a directory, try index.html
        if file_path.is_dir():
            file_path = file_path / "index.html"

        if not file_path.exists():
            self.send_error(404, f"File not found: {url_path}")
            return

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # If it's HTML, inject the reload script
            if file_path.suffix == ".html":
                try:
                    content_str = content.decode("utf-8")
                    if "</body>" in content_str:
                        content_str = content_str.replace(
                            "</body>", self._live_reload_script() + "</body>"
                        )
                        content = content_str.encode("utf-8")
                except (UnicodeDecodeError, AttributeError):
                    pass

            # Send response
            self.send_response(200)
            self.send_header("Content-type", self.guess_type(str(file_path)))
            self.send_header("Content-Length", len(content))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(content)

            if self.path.split("?")[0].endswith(".html") or self.path.split("?")[
                0
            ].endswith("/"):
                print(f"{Colors.BLUE}📄{Colors.RESET} {url_path}")

        except Exception as e:
            self.send_error(500, f"Error serving {url_path}: {e}")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class BuildWatcher(FileSystemEventHandler if HAS_WATCHDOG else object):
    """Watchdog handler for file changes."""

    def __init__(self, builder, rebuild_callback, ignore_patterns=None):
        self.builder = builder
        self.rebuild_callback = rebuild_callback
        self.ignore_patterns = ignore_patterns or {
            ".pyc",
            "__pycache__",
            ".git",
            "~",
            ".tmp",
            ".temp",
            ".swp",
            ".swo",
        }
        self.last_build_time = 0
        self.rebuilding = False
        self.last_event_time = 0.0
        self.min_event_interval = 0.75

    def on_modified(self, event):
        if not self._should_rebuild(event):
            return
        self.rebuild_callback()

    def on_created(self, event):
        if not self._should_rebuild(event):
            return
        self.rebuild_callback()

    def _should_rebuild(self, event):
        """Check if event should trigger rebuild."""
        if event.is_directory:
            return False

        path = Path(event.src_path)
        path_str = str(path)
        now = time.monotonic()

        # Throttle duplicate fs events from a single save operation
        if now - self.last_event_time < self.min_event_interval:
            return False
        self.last_event_time = now

        # Skip ignored patterns
        if any(pattern in path_str for pattern in self.ignore_patterns):
            return False

        # Only watch markdown, HTML, and YAML files
        return path.suffix in {".md", ".html", ".yaml", ".yml", ".jinja", ".jinja2"}


class DevServer:
    """Development server with auto-rebuild."""

    def __init__(
        self, port: int = 8000, rebuild_delay: float = 0.5, output_dir: str = "site"
    ):
        self.port = port
        self.rebuild_delay = rebuild_delay
        self.output_dir = Path(output_dir)
        self.builder = WebsiteBuilder(
            templates_dir="website/templates", output_dir=output_dir
        )
        self.builder.base_url = f"http://127.0.0.1:{port}/"

        self.rebuild_pending = False
        self.reload_version = 0
        self.observer = None
        self.server = None
        self.server_thread = None

    def _bump_reload_version(self):
        """Increment reload version so browsers refresh once per completed build."""
        self.reload_version += 1
        LiveReloadHandler.reload_version = self.reload_version

    def rebuild_site(self):
        """Rebuild the website."""
        if self.rebuild_pending:
            return

        self.rebuild_pending = True

        def do_rebuild():
            time.sleep(self.rebuild_delay)  # Debounce multiple file changes
            try:
                print(f"\n{Colors.YELLOW}🔨 Rebuilding website...{Colors.RESET}")
                start = time.time()
                self.builder.build_site()
                self._bump_reload_version()
                elapsed = time.time() - start
                print(
                    f"{Colors.GREEN}✅ Build complete in {elapsed:.2f}s{Colors.RESET}\n"
                )
            except Exception as e:
                print(f"{Colors.RED}❌ Build failed: {e}{Colors.RESET}\n")
            finally:
                self.rebuild_pending = False

        thread = threading.Thread(target=do_rebuild, daemon=True)
        thread.start()

    def start(self):
        """Start the dev server."""
        print(
            f"""
{Colors.BOLD}🚀 QDrant Loader Dev Server{Colors.RESET}
{Colors.BOLD}═══════════════════════════════════════{Colors.RESET}

📍 Local server: {Colors.BOLD}http://127.0.0.1:{self.port}/{Colors.RESET}
📁 Output dir:   {Colors.BOLD}{self.output_dir}{Colors.RESET}
🔍 Watching:     {Colors.BOLD}docs/, website/templates/{Colors.RESET}
🔄 Live reload:  {Colors.BOLD}Enabled{Colors.RESET}

{Colors.YELLOW}Tip: Open browser and make changes to markdown/templates.
     The site will auto-rebuild and reload!{Colors.RESET}

Press Ctrl+C to stop.
{Colors.BOLD}═══════════════════════════════════════{Colors.RESET}\n
"""
        )

        # Initial build
        print(f"{Colors.YELLOW}📦 Initial build...{Colors.RESET}")
        try:
            self.builder.build_site()
            self._bump_reload_version()
            print(f"{Colors.GREEN}✅ Ready to go!{Colors.RESET}\n")
        except Exception as e:
            print(f"{Colors.RED}❌ Initial build failed: {e}{Colors.RESET}")
            return

        # Start file watcher
        if HAS_WATCHDOG:
            self._start_watchdog()
        else:
            self._start_polling_watcher()

        # Start HTTP server
        self._start_http_server()

    def _start_watchdog(self):
        """Start watchdog observer."""
        watcher = BuildWatcher(self.builder, self.rebuild_site)
        self.observer = Observer()

        # Watch documentation and templates
        for path in ["docs", "website/templates"]:
            if Path(path).exists():
                self.observer.schedule(watcher, path, recursive=True)

        self.observer.start()
        print(f"{Colors.GREEN}👁️  File watcher started (watchdog){Colors.RESET}\n")

    def _start_polling_watcher(self):
        """Fallback: poll file system for changes."""
        watched_paths = set()
        last_mtimes = {}

        def poll_files():
            for base_path in ["docs", "website/templates"]:
                if not Path(base_path).exists():
                    continue

                for file_path in Path(base_path).rglob("*"):
                    if file_path.is_file() and file_path.suffix in {
                        ".md",
                        ".html",
                        ".yaml",
                        ".yml",
                    }:
                        try:
                            mtime = file_path.stat().st_mtime
                            if file_path not in last_mtimes:
                                last_mtimes[file_path] = mtime
                            elif last_mtimes[file_path] != mtime:
                                last_mtimes[file_path] = mtime
                                self.rebuild_site()
                        except OSError:
                            pass

        def watcher_thread():
            while True:
                poll_files()
                time.sleep(1)

        thread = threading.Thread(target=watcher_thread, daemon=True)
        thread.start()
        print(
            f"{Colors.GREEN}👁️  File watcher started (polling fallback){Colors.RESET}\n"
        )

    def _start_http_server(self):
        """Start HTTP server."""
        # Store the repo root directory path
        repo_root = Path.cwd()

        # Set shared state for request handler
        LiveReloadHandler.output_directory = repo_root / self.output_dir
        LiveReloadHandler.reload_version = self.reload_version

        handler = LiveReloadHandler
        with socketserver.TCPServer(("", self.port), handler) as httpd:
            print(
                f"{Colors.GREEN}🌐 Server listening on http://127.0.0.1:{self.port}/{Colors.RESET}\n"
            )
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Shutting down...{Colors.RESET}")
                if self.observer:
                    self.observer.stop()
                    self.observer.join()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="QDrant Loader dev server with auto-rebuild and live reload"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=8000, help="Port to serve on (default: 8000)"
    )
    parser.add_argument(
        "--rebuild-delay",
        "-d",
        type=float,
        default=0.5,
        help="Delay before rebuilding after file change (seconds, default: 0.5)",
    )
    parser.add_argument(
        "--output", "-o", default="site", help="Output directory (default: site)"
    )

    args = parser.parse_args()

    server = DevServer(
        port=args.port, rebuild_delay=args.rebuild_delay, output_dir=args.output
    )
    server.start()


if __name__ == "__main__":
    main()
