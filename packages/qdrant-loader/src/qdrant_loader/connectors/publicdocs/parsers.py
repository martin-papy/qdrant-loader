from __future__ import annotations

import fnmatch
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString


def extract_links(html: str, current_url: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for link in soup.find_all("a", href=True):
        href = str(link["href"])  # type: ignore[index]
        absolute_url = urljoin(current_url, href)
        if absolute_url.startswith(base_url):
            absolute_url = absolute_url.split("#")[0]
            links.append(absolute_url)
    return links


def extract_title(html: str, content_selector: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    content = soup.select_one(content_selector)
    if content:
        h1 = content.find("h1")
        if h1:
            return h1.get_text(strip=True)
        heading = content.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        if heading:
            return heading.get_text(strip=True)
    return "Untitled Document"


def extract_content(
    html: str, content_selector: str, remove: list[str], code_blocks_selector: str
) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for selector in remove:
        for element in soup.select(selector):
            element.decompose()
    content = soup.select_one(content_selector)
    if not content:
        return ""
    code_blocks = content.select(code_blocks_selector)
    for code_block in code_blocks:
        code_text = code_block.get_text()
        if code_text:
            # Keep node in tree: clear and append NavigableString with fenced markdown
            code_block.clear()
            code_block.append(NavigableString(f"\n```\n{code_text}\n```\n"))
    return content.get_text(separator="\n", strip=True)


def should_process_url(
    url: str, base_url: str, exclude_paths: list[str], path_pattern: str | None
) -> bool:
    if not url.startswith(base_url):
        return False
    path = url[len(base_url) :]
    for exclude_path in exclude_paths:
        if fnmatch.fnmatch(path, exclude_path):
            return False
    if path_pattern is None:
        return True
    return fnmatch.fnmatch(path, path_pattern)


def extract_attachments(
    html: str, page_url: str, document_id: str, selectors: list[str]
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    attachments: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for selector in selectors:
        links = soup.select(selector)
        for link in links:
            try:
                href = link.get("href")
                if not href:
                    continue

                # Build absolute URL safely
                absolute_url = urljoin(page_url, str(href))

                # Normalize by stripping fragments and whitespace
                absolute_url = absolute_url.strip().split("#")[0]

                parsed_url = urlparse(absolute_url)

                # Validate scheme and netloc
                if parsed_url.scheme.lower() not in ("http", "https", "ftp"):
                    continue
                if not parsed_url.netloc:
                    continue

                # Deduplicate on normalized absolute URL
                if absolute_url in seen_urls:
                    continue
                seen_urls.add(absolute_url)

                # Derive a safe filename
                if parsed_url.path:
                    filename = parsed_url.path.rsplit("/", 1)[-1] or "download"
                else:
                    filename = "download"

                # If there is no extension, keep generic octet-stream.
                # Preserve multi-part extensions like .tar.gz by taking everything after the first dot.
                file_ext = filename.split(".", 1)[1].lower() if "." in filename else ""
                mime_type = get_mime_type_from_extension(file_ext)

                # Stable id using index in the deduplicated list
                attachment_id = f"{document_id}_{len(attachments)}"

                attachments.append(
                    {
                        "id": attachment_id,
                        "filename": filename or "download",
                        "size": 0,
                        "mime_type": mime_type,
                        "download_url": absolute_url,
                    }
                )
            except Exception:
                # Skip malformed URLs or parsing errors silently; caller can log if needed
                continue

    return attachments


def get_mime_type_from_extension(extension: str) -> str:
    mime_types = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain",
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
        "zip": "application/zip",
    }
    return mime_types.get(extension, "application/octet-stream")
