#!/usr/bin/env python3

import logging
import os
import subprocess
import sys
from pathlib import Path

import requests
import tomli
import tomli_w
from click import command, option
from click.termui import prompt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=False)

# Package definitions
PACKAGES = {
    "qdrant-loader": {
        "path": "packages/qdrant-loader",
        "pyproject": "packages/qdrant-loader/pyproject.toml",
    },
    "qdrant-loader-mcp-server": {
        "path": "packages/qdrant-loader-mcp-server",
        "pyproject": "packages/qdrant-loader-mcp-server/pyproject.toml",
    },
}


# Configure logging
def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(level)  # Explicitly set the level on the logger
    return logger


def get_package_version(package_name: str) -> str:
    """Get the current version from a package's pyproject.toml."""
    logger = logging.getLogger(__name__)
    pyproject_path = PACKAGES[package_name]["pyproject"]
    logger.debug(f"Reading current version from {pyproject_path}")

    if not Path(pyproject_path).exists():
        logger.error(
            f"Package {package_name} pyproject.toml not found at {pyproject_path}"
        )
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        pyproject = tomli.load(f)
    version = pyproject["project"]["version"]
    logger.debug(f"Current version for {package_name}: {version}")
    return version


def get_all_package_versions() -> dict[str, str]:
    """Get current versions for all packages."""
    logger = logging.getLogger(__name__)
    versions = {}
    for package_name in PACKAGES.keys():
        versions[package_name] = get_package_version(package_name)
    logger.info(f"Current package versions: {versions}")
    return versions


def update_package_version(
    package_name: str, new_version: str, dry_run: bool = False
) -> None:
    """Update the version in a package's pyproject.toml."""
    logger = logging.getLogger(__name__)
    pyproject_path = PACKAGES[package_name]["pyproject"]

    if dry_run:
        logger.info(
            f"[DRY RUN] Would update version in {pyproject_path} to {new_version}"
        )
        return

    logger.info(f"Updating version in {pyproject_path} to {new_version}")
    with open(pyproject_path, "rb") as f:
        pyproject = tomli.load(f)

    pyproject["project"]["version"] = new_version

    with open(pyproject_path, "wb") as f:
        tomli_w.dump(pyproject, f)
    logger.debug(f"Version updated successfully for {package_name}")


def update_all_package_versions(
    new_versions: dict[str, str], dry_run: bool = False
) -> None:
    """Update versions for all packages."""
    logger = logging.getLogger(__name__)
    for package_name, new_version in new_versions.items():
        update_package_version(package_name, new_version, dry_run)


def run_command(cmd: str, dry_run: bool = False) -> tuple[str, str]:
    """Run a shell command and return stdout and stderr."""
    logger = logging.getLogger(__name__)
    if dry_run and not cmd.startswith(
        (
            "git status",
            "git branch",
            "git log",
            "git fetch",
            "git rev-list",
            "git remote",
            "git rev-parse",
        )
    ):
        logger.info(f"[DRY RUN] Would execute: {cmd}")
        return "", ""

    logger.debug(f"Executing command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed with return code {result.returncode}")
        logger.error(f"stderr: {result.stderr}")
    return result.stdout.strip(), result.stderr.strip()


def check_git_status(dry_run: bool = False) -> None:
    """Check if the working directory is clean."""
    logger = logging.getLogger(__name__)
    logger.info("Starting git status check...")
    logger.debug("Checking git status")
    stdout, _ = run_command("git status --porcelain", dry_run)
    if stdout:
        logger.error(
            "There are uncommitted changes. Please commit or stash them first."
        )
        sys.exit(1)
    logger.debug("Git status check passed")
    logger.info("Git status check completed successfully")


def check_current_branch(dry_run: bool = False) -> None:
    """Check if we're on the main branch."""
    logger = logging.getLogger(__name__)
    logger.info("Starting current branch check...")
    logger.debug("Checking current branch")
    stdout, _ = run_command("git branch --show-current", dry_run)
    if stdout != "main":
        logger.error("Not on main branch. Please switch to main branch first.")
        sys.exit(1)
    logger.debug("Current branch check passed")
    logger.info("Current branch check completed successfully")


def check_unpushed_commits(dry_run: bool = False) -> None:
    """Check if there are any unpushed commits."""
    logger = logging.getLogger(__name__)
    logger.info("Starting unpushed commits check...")
    logger.debug("Checking for unpushed commits")
    stdout, _ = run_command("git log origin/main..HEAD", dry_run)
    if stdout:
        logger.error(
            "There are unpushed commits. Please push all changes before creating a release."
        )
        sys.exit(1)
    logger.debug("No unpushed commits found")
    logger.info("Unpushed commits check completed successfully")


def get_github_token(dry_run: bool = False) -> str:
    """Get GitHub token from environment variable."""
    logger = logging.getLogger(__name__)
    logger.debug("Getting GitHub token from environment")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN not found in .env file.")
        sys.exit(1)
    return token


def extract_repo_info(git_url: str) -> str:
    """
    Extract GitHub username and repository name from git remote URL.

    Returns the repo info in format "username/repo"
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Extracting repo info from: {git_url}")

    # Handle HTTPS URLs: https://github.com/username/repo.git
    if git_url.startswith("https://github.com/"):
        parts = (
            git_url.replace("https://github.com/", "").replace(".git", "").split("/")
        )
        if len(parts) >= 2:
            repo_path = "/".join(parts[:2])
            logger.debug(f"Extracted repo path from HTTPS URL: {repo_path}")
            return repo_path

    # Handle SSH URLs with ssh:// prefix: ssh://git@github.com/username/repo.git
    elif git_url.startswith("ssh://git@github.com/"):
        parts = (
            git_url.replace("ssh://git@github.com/", "").replace(".git", "").split("/")
        )
        if len(parts) >= 2:
            repo_path = "/".join(parts[:2])
            logger.debug(f"Extracted repo path from SSH URL (with prefix): {repo_path}")
            return repo_path

    # Handle SSH URLs without prefix: git@github.com:username/repo.git
    elif git_url.startswith("git@github.com:"):
        parts = git_url.replace("git@github.com:", "").replace(".git", "").split("/")
        if len(parts) >= 1:
            repo_path = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
            logger.debug(
                f"Extracted repo path from SSH URL (without prefix): {repo_path}"
            )
            return repo_path

    logger.error(f"Could not parse repository path from Git URL: {git_url}")
    sys.exit(1)


def create_github_release(
    package_name: str, version: str, token: str, dry_run: bool = False
) -> None:
    """Create a GitHub release for a specific package."""
    logger = logging.getLogger(__name__)
    tag_name = f"{package_name}-v{version}"

    if dry_run:
        logger.info(
            f"[DRY RUN] Would create GitHub release for {package_name} version {version} with tag {tag_name}"
        )
        return

    logger.info(f"Creating GitHub release for {package_name} version {version}")
    # Get the latest commits for release notes
    stdout, _ = run_command("git log --pretty=format:'%h %s' -n 10")
    release_notes = f"## Changes for {package_name} v{version}\n\n```\n{stdout}\n```"

    # Create release
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "tag_name": tag_name,
        "name": f"{package_name} v{version}",
        "body": release_notes,
        "draft": False,
        "prerelease": "b" in version,
    }

    # Get repository info
    stdout, _ = run_command("git remote get-url origin", dry_run)
    logger.debug(f"Raw Git remote URL: {stdout}")

    repo_url = extract_repo_info(stdout)
    logger.debug(f"Parsed repository URL: {repo_url}")

    response = requests.post(
        f"https://api.github.com/repos/{repo_url}/releases", headers=headers, json=data
    )

    if response.status_code != 201:
        logger.error(
            f"Error creating GitHub release for {package_name}: {response.text}"
        )
        sys.exit(1)
    logger.info(f"GitHub release created successfully for {package_name}")


def check_main_up_to_date(dry_run: bool = False) -> None:
    """Check if local main branch is up to date with remote main."""
    logger = logging.getLogger(__name__)
    logger.info("Starting main branch up-to-date check...")
    logger.debug("Checking if main branch is up to date")
    stdout, _ = run_command("git fetch origin main", dry_run)
    stdout, _ = run_command("git rev-list HEAD...origin/main --count", dry_run)
    if stdout != "0":
        logger.error(
            "Local main branch is not up to date with remote main. Please pull the latest changes first."
        )
        sys.exit(1)
    logger.debug("Main branch is up to date")
    logger.info("Main branch up-to-date check completed successfully")


def check_github_workflows(dry_run: bool = False) -> None:
    """Check if all GitHub Actions workflows are passing."""
    logger = logging.getLogger(__name__)
    logger.info("Starting GitHub workflows check...")
    logger.info("Checking GitHub Actions workflow status")

    # Get repository info
    stdout, _ = run_command("git remote get-url origin", dry_run)
    logger.debug(f"Raw Git remote URL: {stdout}")

    repo_url = extract_repo_info(stdout)
    logger.debug(f"Parsed repository URL: {repo_url}")

    # Get GitHub token
    token = get_github_token(dry_run)
    logger.debug("GitHub token obtained")

    # Get the latest workflow runs
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # First check for running workflows
    logger.debug("Checking for running workflows")
    response = requests.get(
        f"https://api.github.com/repos/{repo_url}/actions/runs",
        headers=headers,
        params={"branch": "main", "status": "in_progress", "per_page": 5},
    )

    if response.status_code != 200:
        logger.error(f"Error checking GitHub Actions status: {response.text}")
        sys.exit(1)

    runs = response.json()["workflow_runs"]
    if runs:
        logger.error(
            "There are workflows still running. Please wait for them to complete."
        )
        for run in runs:
            logger.error(f"- {run['name']} is running: {run['html_url']}")
        sys.exit(1)

    # Get current commit hash
    current_commit, _ = run_command("git rev-parse HEAD", dry_run)
    logger.debug(f"Current commit hash: {current_commit}")

    # Then check completed workflows
    logger.debug("Checking completed workflows")
    response = requests.get(
        f"https://api.github.com/repos/{repo_url}/actions/runs",
        headers=headers,
        params={"branch": "main", "status": "completed", "per_page": 5},
    )

    if response.status_code != 200:
        logger.error(f"Error checking GitHub Actions status: {response.text}")
        sys.exit(1)

    runs = response.json()["workflow_runs"]
    if not runs:
        logger.error(
            "No recent workflow runs found. Please ensure workflows are running."
        )
        sys.exit(1)

    # Check the most recent run for each workflow
    workflows = {}
    for run in runs:
        workflow_name = run["name"]
        if workflow_name not in workflows:
            workflows[workflow_name] = run

    for workflow_name, run in workflows.items():
        if run["conclusion"] != "success":
            logger.error(
                f"Workflow '{workflow_name}' is not passing. Latest run status: {run['conclusion']}"
            )
            logger.error(f"Please check the workflow run at: {run['html_url']}")
            sys.exit(1)

        # Check if the workflow run matches our current commit
        if run["head_sha"] != current_commit:
            logger.error(
                f"Workflow '{workflow_name}' was run on a different commit. Please ensure all workflows are run on the current commit."
            )
            logger.error(f"Current commit: {current_commit}")
            logger.error(f"Workflow commit: {run['head_sha']}")
            logger.error(f"Workflow run: {run['html_url']}")
            sys.exit(1)

    logger.info("All workflows are passing and match the current commit")
    logger.info("GitHub workflows check completed successfully")


def calculate_new_version(
    current_version: str, bump_type: int, custom_version: str | None = None
) -> str:
    """Calculate new version based on bump type."""
    if bump_type == 5 and custom_version is not None:
        return custom_version

    if bump_type == 1:  # Major
        major, minor, patch = map(int, current_version.split(".")[:3])
        return f"{major + 1}.0.0"
    elif bump_type == 2:  # Minor
        major, minor, patch = map(int, current_version.split(".")[:3])
        return f"{major}.{minor + 1}.0"
    elif bump_type == 3:  # Patch
        major, minor, patch = map(int, current_version.split(".")[:3])
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type == 4:  # Beta
        if "b" in current_version:
            base_version, beta_num = current_version.split("b")
            return f"{base_version}b{int(beta_num) + 1}"
        else:
            return f"{current_version}b1"

    return current_version


@command()
@option(
    "--dry-run",
    is_flag=True,
    help="Simulate the release process without making any changes",
)
@option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def release(dry_run: bool = False, verbose: bool = False):
    """Create a new release and bump version for both packages."""
    # Setup logging
    logger = setup_logging(verbose)

    if dry_run:
        logger.info(
            "Running in dry-run mode. No changes will be made, but all safety checks will be performed."
        )

    # Run safety checks
    check_git_status(dry_run)
    check_current_branch(dry_run)
    check_unpushed_commits(dry_run)
    check_main_up_to_date(dry_run)
    check_github_workflows(dry_run)

    if dry_run:
        logger.info(
            "All safety checks passed. In a real run, the following changes would be made:"
        )

    current_versions = get_all_package_versions()

    # Display current versions
    logger.info("\nCurrent package versions:")
    for package_name, version in current_versions.items():
        logger.info(f"  {package_name}: {version}")

    # Get new version strategy
    logger.info("\nVersion bump options:")
    logger.info("1. Major (e.g., 1.0.0)")
    logger.info("2. Minor (e.g., 0.2.0)")
    logger.info("3. Patch (e.g., 0.1.4)")
    logger.info("4. Beta (e.g., 0.1.3b2)")
    logger.info("5. Custom")

    choice = prompt("Select version bump type", type=int)

    custom_version = None
    if choice == 5:
        custom_version = prompt("Enter new version")
        if not custom_version:
            logger.error("Version cannot be empty")
            sys.exit(1)
    elif choice not in [1, 2, 3, 4]:
        logger.error("Invalid choice")
        sys.exit(1)

    # Calculate new versions for all packages
    new_versions = {}
    for package_name, current_version in current_versions.items():
        new_version = calculate_new_version(current_version, choice, custom_version)
        new_versions[package_name] = new_version

    # Display planned changes
    logger.info("\nPlanned version changes:")
    for package_name in PACKAGES.keys():
        logger.info(
            f"  {package_name}: {current_versions[package_name]} -> {new_versions[package_name]}"
        )

    if dry_run:
        logger.info("\n[DRY RUN] Would perform the following actions:")
        for package_name, current_version in current_versions.items():
            logger.info(
                f"[DRY RUN] Would create and push tag {package_name}-v{current_version}"
            )
            logger.info(
                f"[DRY RUN] Would create release for {package_name} version {current_version}"
            )

        for package_name, new_version in new_versions.items():
            logger.info(
                f"[DRY RUN] Would update {package_name} version to {new_version}"
        )

        logger.info(f"[DRY RUN] Would create commit: chore(release): bump versions")
        return

    # Create and push tags with current versions
    for package_name, current_version in current_versions.items():
        tag_name = f"{package_name}-v{current_version}"
        run_command(
            f'git tag -a {tag_name} -m "Release {package_name} v{current_version}"',
            dry_run,
        )

    run_command("git push origin main --tags", dry_run)

    # Create GitHub releases with current versions
    token = get_github_token(dry_run)
    for package_name, current_version in current_versions.items():
        create_github_release(package_name, current_version, token, dry_run)

    # Update versions for all packages
    update_all_package_versions(new_versions, dry_run)

    # Create commit with all version updates
    run_command("git add packages/*/pyproject.toml", dry_run)
    run_command('git commit -m "chore(release): bump versions"', dry_run)

    logger.info("\nSuccessfully created releases for all packages and bumped versions!")
    logger.info("Released versions:")
    for package_name, version in current_versions.items():
        logger.info(f"  {package_name}: v{version}")
    logger.info("New versions:")
    for package_name, version in new_versions.items():
        logger.info(f"  {package_name}: v{version}")


if __name__ == "__main__":
    release()
