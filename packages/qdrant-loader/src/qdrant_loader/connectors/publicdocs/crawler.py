from __future__ import annotations

import fnmatch
from typing import Any
from urllib.parse import urljoin, urlparse

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
    # Support both aiohttp-style context manager and direct-await mocks
    status_code = None
    response = None
    html = ""
    context_managed = False
    try:
        get_result = session.get(base_url)

        # Prefer async context manager usage if supported (aiohttp-style)
        if hasattr(get_result, "__aenter__") and hasattr(get_result, "__aexit__"):
            context_managed = True
            async with get_result as resp:  # type: ignore[func-returns-value]
                response = resp
                status = getattr(response, "status", None)
                status_code = status
                if status is None or not (200 <= int(status) < 300):
                    logger.warning(
                        "Non-2xx HTTP status when fetching base URL",
                        url=base_url,
                        status_code=status,
                    )
                    return []
                try:
                    html = await _read_text(response)
                except Exception as e:
                    logger.warning(
                        "Failed to read HTTP response body", url=base_url, error=str(e)
                    )
                    return []
        else:
            # Otherwise await if it's awaitable, or use it directly
            if hasattr(get_result, "__await__"):
                response = await get_result  # type: ignore[assignment]
            else:
                response = get_result

            status = getattr(response, "status", None)
            status_code = status
            if status is None or not (200 <= int(status) < 300):
                logger.warning(
                    "Non-2xx HTTP status when fetching base URL",
                    url=base_url,
                    status_code=status,
                )
                return []
            try:
                html = await _read_text(response)
            except Exception as e:
                logger.warning(
                    "Failed to read HTTP response body", url=base_url, error=str(e)
                )
                return []
    except Exception as e:
        logger.warning("HTTP request failed", url=base_url, error=str(e))
        return []
    finally:
        # Best-effort close for non-context-managed responses
        if response is not None and not context_managed:
            close = getattr(response, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    if status_code is not None:
        logger.debug("HTTP request successful", status_code=status_code)
    logger.debug(
        "Received HTML response",
        status_code=status_code,
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
                if not (
                    abs_path == base_path_norm
                    or abs_path.startswith(base_path_norm + "/")
                ):
                    continue

            if not any(exclude in absolute_url for exclude in exclude_paths) and (
                path_pattern is None or fnmatch.fnmatch(parsed.path, path_pattern)
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
