from __future__ import annotations

from typing import Any, cast
from urllib.parse import urljoin

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

    for link in soup.find_all("a"):
        try:
            href = str(cast(BeautifulSoup, link)["href"])  # type: ignore
            if not href or not isinstance(href, str):
                continue

            if href.startswith("#"):
                continue

            absolute_url = urljoin(base_url, href)
            absolute_url = absolute_url.split("#")[0]

            if (
                absolute_url.startswith(base_url)
                and absolute_url not in pages
                and not any(exclude in absolute_url for exclude in exclude_paths)
                and (
                    not path_pattern
                    or __import__("fnmatch").fnmatch(absolute_url, path_pattern)
                )
            ):
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


