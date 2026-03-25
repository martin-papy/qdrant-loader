"""Generate a CHANGELOG.md section from git commits since the last release tag."""

import re
import subprocess
from collections import defaultdict
from datetime import date
from pathlib import Path

import click

REPO_ROOT = Path(__file__).parent
DEFAULT_CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
GITHUB_COMPARE_BASE = "https://github.com/martin-papy/qdrant-loader/compare"

CHANGELOG_HEADER = """\
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""

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
CATEGORY_ORDER = ["Removed", "Fixed", "Added", "Changed", "Deprecated", "Security"]
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
    """Run a git command in the repo root and return stripped stdout."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def latest_release_tag() -> str:
    """Return the most recent ``qdrant-loader-v*`` git tag sorted by version."""
    tags = git(
        "tag", "--list", "qdrant-loader-v*", "--sort=-version:refname"
    ).splitlines()
    if not tags:
        raise click.ClickException("No qdrant-loader-v* tags found.")
    return tags[0]  # first element is latest release


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
        commits.append(
            {
                "hash": parts[0].strip(),
                "subject": parts[1].strip(),
                "body": parts[2].strip() if len(parts) > 2 else "",
            }
        )
    return commits


def should_skip(subject: str) -> bool:
    """Return True if a commit subject should be excluded from the changelog.

    Skips merge commits, release bumps, doc-only changes, reverts, and
    hot-fix entries that were subsequently reverted.
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
    """Extract a GitHub issue number from a commit message.

    Looks for keywords ``Resolves``, ``Fixes``, or ``Closes`` followed by
    ``#NNN`` in either the commit body or the subject line.
    """
    for text in (body, subject):
        m = re.search(r"(?:Resolves|Fixes|Closes)\s+#(\d+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def changed_packages(commit_hash: str) -> list[str]:
    """Return the list of packages touched by a commit, inferred from file paths.

    Runs ``git diff-tree`` to list files changed by the commit and maps each
    file path to a package using the ``PATH_TO_PACKAGE`` prefix table.
    Root-level changes (outside any package directory) are not included.
    """
    files = git(
        "diff-tree", "--no-commit-id", "-r", "--name-only", commit_hash
    ).splitlines()
    found = set()
    for f in files:
        for prefix, package in PATH_TO_PACKAGE.items():
            if f.startswith(prefix):
                found.add(package)
    return list(found)


def build_reference(issue: str | None, pr: str | None, commit_hash: str) -> str:
    """Build a changelog reference string (``[#177]`` or ``[c72a872]``).

    Priority: issue number > PR number > short commit hash.
    """
    ref = issue or pr
    if ref:
        return f"[#{ref}]"
    return f"[{commit_hash[:7]}]"


def process_commits(commits: list[dict]) -> dict:
    """Transform raw commits into ``{ category: { package: [entry_line, ...] } }``.

    For each commit: skips noise, maps the commit type to a changelog category,
    resolves package(s) from scope or changed file paths, and builds the
    formatted entry line. A ``None`` package key means the entry is root-level.
    """
    result = defaultdict(lambda: defaultdict(list))

    for c in commits:
        if should_skip(c["subject"]):
            continue

        commit_type, scope, description, pr = parse_subject(c["subject"])

        category = TYPE_TO_CATEGORY.get(commit_type or "", None)
        if category is None:
            continue

        if not description:
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
    """Render the changelog section for *version* as a Markdown string.

    Categories follow ``CATEGORY_ORDER``; packages follow ``PACKAGE_ORDER``.
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
    """Build the Markdown footer comparison link for *version*."""
    new_tag = f"qdrant-loader-v{version}"
    return f"[{version}]: {GITHUB_COMPARE_BASE}/{from_tag}...{new_tag}"


def prepend_to_changelog(
    section: str, footer_link: str, version: str, changelog_path: Path
) -> None:
    """Prepend a new changelog section and its footer link to *changelog_path*.

    If the file is empty or has no ``## [`` heading yet, the standard Keep a
    Changelog header is written first so the script works on fresh files.
    """
    content = changelog_path.read_text() if changelog_path.exists() else ""

    first_version_match = re.search(r"^## \[", content, re.MULTILINE)

    if first_version_match:
        insert_at = first_version_match.start()
        new_content = content[:insert_at] + section + "\n" + content[insert_at:]
    else:
        header = content if content.strip() else CHANGELOG_HEADER
        new_content = header.rstrip() + "\n\n" + section

    first_link_match = re.search(r"^\[[\d.]+\]:", new_content, re.MULTILINE)
    if first_link_match:
        link_at = first_link_match.start()
        new_content = new_content[:link_at] + footer_link + "\n" + new_content[link_at:]
    else:
        new_content = new_content.rstrip() + "\n\n" + footer_link + "\n"

    changelog_path.write_text(new_content)
    click.echo(f"{changelog_path.name} updated with version {version}.", err=True)


@click.command()
@click.option(
    "--from-tag", default=None, help="Start ref (default: latest qdrant-loader-v* tag)."
)
@click.option("--to-ref", default="HEAD", show_default=True, help="End ref.")
@click.option("--version", required=True, help="New version string, e.g. 0.9.0.")
@click.option(
    "--date",
    "release_date",
    default=str(date.today()),
    show_default=True,
    help="Release date.",
)
@click.option(
    "--changelog-file",
    "changelog_file",
    default=str(DEFAULT_CHANGELOG_PATH),
    show_default=True,
    help="Path to the changelog file.",
)
@click.option(
    "--write",
    "do_write",
    is_flag=True,
    default=False,
    help="Write result to the changelog file.",
)
def main(from_tag, to_ref, version, release_date, changelog_file, do_write):
    """Generate a CHANGELOG section from commits since the last release tag.

    By default, prints the generated section to stdout so you can review it
    before committing. Pass ``--write`` to prepend it directly to the
    changelog file and append the version comparison link to the footer.

    Examples::

        # Preview the draft for an upcoming 0.9.0 release
        python generate_changelog.py --version 0.9.0

        # Write directly to CHANGELOG.md
        python generate_changelog.py --version 0.9.0 --write

        # Write to a different file for testing
        python generate_changelog.py --version 0.9.0 --write --changelog-file TEST_CHANGELOG.md

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
        prepend_to_changelog(section, footer_link, version, Path(changelog_file))
    else:
        click.echo(section)
        click.echo(footer_link)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
