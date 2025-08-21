from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse
import fnmatch

from bs4 import BeautifulSoup

from qdrant_loader.connectors.publicdocs.http import read_text_response as _read_text


async def discover_pages(
    session: Any,
    base_url: str,
    *,
    path_pattern: str | None,
    exclude_paths: list[str],
    logger: Any,
) -> list[str]:
    """Fetch the base URL and discover matching pages under it."""
    response = await session.get(base_url)
    html = await _read_text(response)

    logger.debug("HTTP request successful", status_code=response.status)
    logger.debug(
        "Received HTML response",
        status_code=response.status,
        content_length=len(html),
    )

    soup = BeautifulSoup(html, "html.parser")
    pages = [base_url]
    seen: set[str] = {base_url}
    base_parsed = urlparse(base_url)
    base_netloc = base_parsed.netloc
    base_path = base_parsed.path or ""

    for link in soup.find_all("a"):
        try:
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            if href.startswith("#"):
                continue

            absolute_url = urljoin(base_url, href)
            absolute_url = absolute_url.split("#")[0]
            parsed = urlparse(absolute_url)

            # Validate scheme
            if parsed.scheme not in ("http", "https"):
                continue

            # Enforce same-origin
            if parsed.netloc != base_netloc:
                continue

            # Enforce base path scope
            abs_path = parsed.path or "/"
            base_path_norm = base_path.rstrip("/")
            if base_path_norm:
                if not (abs_path == base_path_norm or abs_path.startswith(base_path_norm + "/")):
                    continue

            if (
                not any(exclude in absolute_url for exclude in exclude_paths)
                and (
                    path_pattern is None
                    or fnmatch.fnmatch(parsed.path, path_pattern)
                )
            ):
                if absolute_url not in seen:
                    seen.add(absolute_url)
                    logger.debug("Found valid page URL", url=absolute_url)
                    pages.append(absolute_url)
        except Exception as e:  # pragma: no cover - best-effort crawl
            logger.warning(
                "Failed to process link",
                href=str(link.get("href", "")),  # type: ignore
                error=str(e),
            )
            continue
    logger.debug("Page discovery completed", total_pages=len(pages), pages=pages)
    return pages


