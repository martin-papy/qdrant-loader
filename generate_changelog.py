"""Generate a CHANGELOG.md section from git commits since the last release tag."""

import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import click

REPO_ROOT = Path(__file__).parent
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
GITHUB_COMPARE_BASE = "https://github.com/martin-papy/qdrant-loader/compare"

# Commit type → changelog category
TYPE_TO_CATEGORY = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "chore": "Changed",
    "remove": "Removed",
    "deprecate": "Deprecated",
    "security": "Security",
}

# Scope → package. display name
SCOPE_TO_PACKAGE = {
    "mcp": "Qdrant-loader-mcp-server",
    "core": "Qdrant-loader-core",
    "loader": "Qdrant-loader",
}

# File path prefix → package display name
PATH_TO_PACKAGE = {
    "packages/qdrant-loader-mcp-server/": "Qdrant-loader-mcp-server",
    "packages/qdrant-loader-core/": "Qdrant-loader-core",
    "packages/qdrant-loader/": "Qdrant-loader",  
}

# Ordered input
CATEGORY_ORDER  = ["Removed", "Fixed", "Added", "Changed", "Deprecated", "Security"]
PACKAGE_ORDER = ["Qdrant-loader", "Qdrant-loader-core", "Qdrant-loader-mcp-server"]

# Commit subjects to skip (regular expressions)
SKIP_PATTERNS = [
    r"^Merge (pull request|branch)",
    r"^chore\(release\):",
    r"^chore(\(doc\))?:\s*(update changelog|fix wording|update readme)",
    r"^docs:",
    r"^Revert\b",
    r"^hot fix:",  # reverted hot fixes already in changelog
]

def git(*args) -> str:
    """Run a git command in the repo root and return stdout as a stripped string
    Args:
        *args: Git subcommand and arguments

    Returns:
        The stripped stdout output of the command
    """
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def latest_release_tag() -> str:
    """Return the most recent `qdrant-loader-v*` git tag sorted by version
    
    Args:
        None
    
    Returns:
        The tag name of the latest release
    """
    tags = git("tag", "--list", "qdrant-loader-v*", "--sort=-version:refname").splitlines()
    if not tags:
        raise click.ClickException("No qdrant-loader-v* tags found.")
    return tags[0] # first element is latest release


def previous_release_tag(current_tag: str) -> str:
    """Return the `qdrant-loader-v*` tag that precededs the given tag.
    
    Args:
        current_tag: The tag to look behind

    Returns:
        The tag name immediately before `current_tag` in version order
    """
    tags = git("tag", "--list", "qdrant-loader-v*", "--sort=-version:refname").splitlines()
    try:
        idx = tags.index(current_tag)
        return tags[idx + 1]
    except (ValueError, IndexError):
        raise click.ClickException(f"Could not find tag before {current_tag}.")
    
    
def get_commits(from_tag: str, to_ref: str) -> list[dict]:
    """Collect all commits in the range `from_tag..to_ref`
    
    Uses ``\\x1f`` (unit separator) and ``\\x1e`` (record separator) as
    delimiters in the git log format to safely handle subjects and bodies
    that contain newlines or colons.

    Args:
        from_tag: The exclusive start ref (e.g. a tag or commit hash).
        to_ref: The inclusive end ref (e.g. ``HEAD`` or a branch name).

    Returns:
        A list of dicts, each with keys ``hash``, ``subject``, and ``body``.
    """
    log = git("log", f"{from_tag}..{to_ref}", "--format=%H\x1f%s\x1f%b\x1e")
    entries = [e.strip() for e in log.split("\x1e") if e.strip()]
    commits = []
    for entry in entries:
        parts = entry.split("\x1f", 2)
        commits.append({
            "hash": parts[0].strip(),
            "subject": parts[1].strip(),
            "body": parts[2].strip() if len(parts) > 2 else "",
        })
    return commits


def should_skip(subject: str) -> bool:
    """Return True if a commit subject should be excluded from the changelog
    
    Skips merge commits, release bumps, doc-only changes, reverts, and hot-fix entries that were subsequetly reverted

    Args:
        subject: The first line of a commit message

    Returns:
        `True` if the commit should be ignored, `False` otherwise.
    """
    return any(re.match(p, subject, re.IGNORECASE) for p in SKIP_PATTERNS)

def parse_subject(subject: str) -> tuple[str | None, str | None, str, str | None]:
    """Parse a conventional commit subject into its constituent parts.

    Handles the format `type(scope): description (#PR)` and strips the
    trailing PR reference before returning the clean description.

    Args:
        subject: The commit subject line

    Returns:
        A 4-tuple of `(type, scope, description, pr_number)`.
        Any field that cannot be extracted is `None`.
    """
    pr_number = None
    pr_match = re.search(r"\s*\(#(\d+)\)\s*$", subject)
    if pr_match:
        pr_number = pr_match.group(1)
        subject = subject[: pr_match.start()]

    conv_match = re.match(r"^(\w+)(?:\(([^)]+)\))?!?:\s*(.+)$", subject)
    if conv_match:
        return conv_match.group(1), conv_match.group(2), conv_match.group(3), pr_number

    return None, None, subject, pr_number


def extract_issue(body: str, subject: str) -> str | None:
    """Extracta GitHub issue number from a commit message
    
    Looks for keywords `Resolves`, `Fixes`, or `Closes` followed by
    `#NNN` in either commit body or the subject line.

    Args:
        body: The multi-line body of the commit message.
        subject: The subject line of the commit message.

    Returns:
        The issue number as string (e.g., `"177"`) or `None` if not found.
    """
    for text in (body, subject):
        m = re.search(r"(?:Resolves|Fixes|Closes)\s+#(\d+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def changed_packages(commit_hash: str) -> list[str]:
    """Return the list of packages touched by a commit, inferred from file paths
    
    Runs ``git diff-tree`` to list files changed by the commit and maps each
    file path to a package using the ``PATH_TO_PACKAGE`` prefix table.
    A commit that touches multiple packages will return multiple entries.
    Root-level changes (outside any package directory) are not included 
    
    Args:
        commit_hash: The full or abbreviated SHA of the commit.

    Returns:
        A deduplicated list of apacakge display names, e.g.,
        ``["Qdrant-loader-mcp-server", "Qdrant-loader-core"]``
    """
    files = git("diff-tree", "--no-commit-id", "-r", "--name-only", commit_hash).splitlines()
    found = set()
    for f in files:
        for prefix, package in PATH_TO_PACKAGE.items():
            if f.startswith(prefix):
                found.add(package)
    return list(found)


def build_reference(issue: str | None, pr: str | None, commit_hash: str) -> str:
    """Build a changelog reference string from an issue number, PR number, or commit hash.

    Priority: issue number > PR number > short commit hash. This matches the existing
    CHANGELOG.md convention where issue refs like`[#177]` are preferred, with `[commithash]`
    as a fallback for commits not linked to an issue or PR.
    
    Args:
        issue: GitHub issue number as a string, or `None`.
        pr: GitHub pull request number as a string, or `None.
        commit_hash: The full commit SHA used to generate a 7-character fallback.

    Returns:
        A reference string such as `"[#177]"` or `"[c72a872]"`
    """
    ref = issue or pr
    if ref:
        return f"[#{ref}]"
    return f"[{commit_hash[:7]}]"


def process_commits(commits: list[dict]) -> dict:
    """Transform a list of raw commits intoa structured changelog data dict.
    
    For each commit:
        - Skips noise (merges, release bumps, etc.)
        - Maps the commit type to a changelog category
        - Resolves the package(s) from scope or changed file paths
        - Builds the formatted entry line

        The returned structure groups entries as
        ``{ category: { package_or_None: [entry_line, ...] } }``
        where a `None` key means the entry has no package sub-creation
    
    Args:
        commits: List of commit dicts as returned by :func:`get_commits`.

    Returns:
        A nested defaultdict of ``{ category: { package: [lines] } }``
    """
    result = defaultdict(lambda: defaultdict(list))

    for c in commits:
        if should_skip(c["subject"]):
            continue

        commit_type, scope, description, pr = parse_subject(c["subject"])

        category = TYPE_TO_CATEGORY.get(commit_type or "", None)
        if category is None:
            continue

        issue = extract_issue(c["body"], c["subject"])
        ref = build_reference(issue, pr, c["hash"])

        if scope and scope in SCOPE_TO_PACKAGE:
            packages = [SCOPE_TO_PACKAGE[scope]]
        else:
            packages = changed_packages(c["hash"])

        description = description[0].upper() + description[1:]
        entry = f"- {description} {ref}"

        if packages:
            for pkg in packages:
                result[category][pkg].append(entry)
        else:
            result[category][None].append(entry)

    return result


def render_section(version: str, release_date: str, data: dict) -> str:
    """Render the full changelog section for a new version as a Markdown string.

    Categories are emitted in the order defined by ``CATEGORY_ORDER``
    (Removed → Fixed → Added → Changed → Deprecated → Security).
    Within each category, packages are ordered per ``PACKAGE_ORDER``, with
    root-level entries (``None`` key) appearing before any sub-sections.

    Args:
        version: The new version string, e.g. ``"0.9.0"``.
        release_date: ISO-format date string, e.g. ``"2026-03-25"``.
        data: Nested dict as returned by :func:`process_commits`.

    Returns:
        A Markdown string for the new changelog section, ending with a newline.
    """
    lines = [f"## [{version}] - {release_date}", ""]

    for category in CATEGORY_ORDER:
        if category not in data:
            continue
        lines.append(f"### {category}")
        lines.append("")

        packages = data[category]

        if None in packages:
            for entry in packages[None]:
                lines.append(entry)
            lines.append("")

        for pkg in PACKAGE_ORDER:
            if pkg not in packages:
                continue
            lines.append(f"#### {pkg}")
            lines.append("")
            for entry in packages[pkg]:
                lines.append(entry)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_footer_link(version: str, from_tag: str) -> str:
    """Build the Markdown footer comparison link for the new version.

    Produces a line like:
    ``[0.9.0]: https://github.com/.../compare/qdrant-loader-v0.8.0...qdrant-loader-v0.9.0``

    Args:
        version: The new version string, e.g. ``"0.9.0"``.
        from_tag: The previous release tag, e.g. ``"qdrant-loader-v0.8.0"``.

    Returns:
        A single-line Markdown link definition string.
    """
    new_tag = f"qdrant-loader-v{version}"
    return f"[{version}]: {GITHUB_COMPARE_BASE}/{from_tag}...{new_tag}"


def prepend_to_changelog(section: str, footer_link: str, version: str) -> None:
    """Prepend a new changelog section to CHANGELOG.md and insert its footer link.

    The section is inserted immediately before the first existing ``## [``
    version heading. The footer link is inserted before the first existing
    link definition line so the most recent version appears at the top of
    the footer block, consistent with the current file structure.

    Args:
        section: The rendered Markdown section from :func:`render_section`.
        footer_link: The footer link line from :func:`build_footer_link`.
        version: The new version string, used only for the confirmation message.

    Raises:
        click.ClickException: If no ``## [`` heading is found in CHANGELOG.md,
            meaning the file structure is unrecognised.
    """
    content = CHANGELOG_PATH.read_text()

    first_version_match = re.search(r"^## \[", content, re.MULTILINE)
    if not first_version_match:
        raise click.ClickException("Could not find insertion point in CHANGELOG.md.")

    insert_at = first_version_match.start()
    new_content = content[:insert_at] + section + "\n" + content[insert_at:]

    first_link_match = re.search(r"^\[[\d.]+\]:", new_content, re.MULTILINE)
    if first_link_match:
        link_at = first_link_match.start()
        new_content = new_content[:link_at] + footer_link + "\n" + new_content[link_at:]
    else:
        new_content = new_content.rstrip() + "\n" + footer_link + "\n"

    CHANGELOG_PATH.write_text(new_content)
    click.echo(f"CHANGELOG.md updated with version {version}.", err=True)


@click.command()
@click.option("--from-tag", default=None, help="Start ref (default: latest qdrant-loader-v* tag).")
@click.option("--to-ref", default="HEAD", show_default=True, help="End ref.")
@click.option("--version", required=True, help="New version string, e.g. 0.9.0.")
@click.option("--date", "release_date", default=str(date.today()), show_default=True, help="Release date.")
@click.option("--write", "do_write", is_flag=True, default=False, help="Write result to CHANGELOG.md.")
def main(from_tag, to_ref, version, release_date, do_write):
    """Generate a CHANGELOG section from commits since the last release tag.

    By default, prints the generated section to stdout so you can review it
    before committing. Pass ``--write`` to prepend it directly to CHANGELOG.md
    and append the version comparison link to the footer.

    Examples::

        # Preview the draft for an upcoming 0.9.0 release
        python generate_changelog.py --version 0.9.0

        # Write directly to CHANGELOG.md
        python generate_changelog.py --version 0.9.0 --write

        # Generate from a specific base tag
        python generate_changelog.py --version 0.9.0 --from-tag qdrant-loader-v0.7.6
    """
    if from_tag is None:
        from_tag = latest_release_tag()
        click.echo(f"Using base tag: {from_tag}", err=True)

    commits = get_commits(from_tag, to_ref)
    click.echo(f"Found {len(commits)} commits since {from_tag}.", err=True)

    data = process_commits(commits)
    section = render_section(version, release_date, data)
    footer_link = build_footer_link(version, from_tag)

    if do_write:
        prepend_to_changelog(section, footer_link, version)
    else:
        click.echo(section)
        click.echo(footer_link)


if __name__ == "__main__":
    main()


