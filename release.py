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

    # Create a custom formatter for cleaner output
    class CleanFormatter(logging.Formatter):
        def format(self, record):
            if record.levelname == "INFO":
                return record.getMessage()
            elif record.levelname == "ERROR":
                return f"❌ {record.getMessage()}"
            elif record.levelname == "DEBUG":
                return f"🔍 {record.getMessage()}"
            else:
                return f"{record.levelname}: {record.getMessage()}"

    # Remove any existing handlers
    logger = logging.getLogger(__name__)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CleanFormatter())

    logging.basicConfig(level=level, handlers=[console_handler], force=True)

    logger.setLevel(level)
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


def get_current_version() -> str:
    """Get the current version from the main package."""
    logger = logging.getLogger(__name__)
    # Use qdrant-loader as the source of truth for version
    main_package = "qdrant-loader"
    version = get_package_version(main_package)
    logger.debug(f"Current version: {version}")
    return version


def get_all_package_versions() -> dict[str, str]:
    """Get current versions for all packages (should all be the same)."""
    logger = logging.getLogger(__name__)
    versions = {}
    for package_name in PACKAGES.keys():
        versions[package_name] = get_package_version(package_name)
    logger.debug(f"Current package versions: {versions}")

    # Check if all versions are the same
    unique_versions = set(versions.values())
    if len(unique_versions) > 1:
        logger.error(
            f"❌ Version mismatch detected! All packages should have the same version."
        )
        for package_name, version in versions.items():
            logger.error(f"   {package_name}: {version}")
        logger.error("Please sync all package versions before running the release.")
        sys.exit(1)

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


def sync_all_package_versions(target_version: str, dry_run: bool = False) -> None:
    """Sync all packages to the same version."""
    logger = logging.getLogger(__name__)
    logger.info(f"Syncing all packages to version {target_version}")
    for package_name in PACKAGES.keys():
        update_package_version(package_name, target_version, dry_run)


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
        logger.debug(f"[DRY RUN] Would execute: {cmd}")
        return "", ""

    logger.debug(f"Executing command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Error: {result.stderr}")
    return result.stdout.strip(), result.stderr.strip()


def check_git_status(dry_run: bool = False) -> bool:
    """Check if the working directory is clean."""
    logger = logging.getLogger(__name__)
    logger.debug("Checking git status")
    stdout, _ = run_command("git status --porcelain", dry_run)
    if stdout:
        logger.error(
            "There are uncommitted changes. Please commit or stash them first."
        )
        if not dry_run:
            sys.exit(1)
        return False
    logger.debug("Git status check passed")
    return True


def check_current_branch(dry_run: bool = False) -> bool:
    """Check if we're on the main branch."""
    logger = logging.getLogger(__name__)
    logger.debug("Checking current branch")
    stdout, _ = run_command("git branch --show-current", dry_run)
    if stdout != "main":
        logger.error("Not on main branch. Please switch to main branch first.")
        if not dry_run:
            sys.exit(1)
        return False
    logger.debug("Current branch check passed")
    return True


def check_unpushed_commits(dry_run: bool = False) -> bool:
    """Check if there are any unpushed commits."""
    logger = logging.getLogger(__name__)
    logger.debug("Checking for unpushed commits")
    stdout, _ = run_command("git log origin/main..HEAD", dry_run)
    if stdout:
        logger.error(
            "There are unpushed commits. Please push all changes before creating a release."
        )
        if not dry_run:
            sys.exit(1)
        return False
    logger.debug("No unpushed commits found")
    return True


def get_github_token(dry_run: bool = False) -> str:
    """Get GitHub token from environment variable."""
    logger = logging.getLogger(__name__)
    logger.debug("Getting GitHub token from environment")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN not found in .env file.")
        if not dry_run:
            sys.exit(1)
        return ""
    return token


def extract_repo_info(git_url: str, dry_run: bool = False) -> str:
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
    if dry_run:
        return "unknown/repo"
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

    repo_url = extract_repo_info(stdout, dry_run)
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


def check_main_up_to_date(dry_run: bool = False) -> bool:
    """Check if local main branch is up to date with remote main."""
    logger = logging.getLogger(__name__)
    logger.debug("Checking if main branch is up to date")
    stdout, _ = run_command("git fetch origin main", dry_run)
    stdout, _ = run_command("git rev-list HEAD...origin/main --count", dry_run)
    if stdout != "0":
        logger.error(
            "Local main branch is not up to date with remote main. Please pull the latest changes first."
        )
        if not dry_run:
            sys.exit(1)
        return False
    logger.debug("Main branch is up to date")
    return True


def check_github_workflows(dry_run: bool = False) -> bool:
    """Check if all GitHub Actions workflows are passing."""
    logger = logging.getLogger(__name__)
    logger.debug("Checking GitHub Actions workflow status")

    # Get repository info
    stdout, _ = run_command("git remote get-url origin", dry_run)
    logger.debug(f"Raw Git remote URL: {stdout}")

    repo_url = extract_repo_info(stdout, dry_run)
    logger.debug(f"Parsed repository URL: {repo_url}")

    if repo_url == "unknown/repo" and dry_run:
        logger.error("Could not parse repository URL - this would fail in a real run")
        return False

    # Get GitHub token
    token = get_github_token(dry_run)
    if not token and dry_run:
        logger.error("GitHub token not available - this would fail in a real run")
        return False
    elif not token:
        return False

    logger.debug("GitHub token obtained")

    # Get the latest workflow runs
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # First check for running workflows
    logger.debug("Checking for running workflows")

    if dry_run:
        logger.debug("[DRY RUN] Would check for running workflows via GitHub API")
        logger.debug("[DRY RUN] Would check completed workflows via GitHub API")
        logger.debug(
            "[DRY RUN] Would verify all workflows are passing and match current commit"
        )
        return True

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
    return True


def calculate_new_version(
    current_version: str, bump_type: int, custom_version: str | None = None
) -> str:
    """Calculate new version based on bump type."""
    if bump_type == 5 and custom_version is not None:
        return custom_version

    # Handle beta versions by extracting base version
    base_version = current_version
    if "b" in current_version:
        base_version = current_version.split("b")[0]

    if bump_type == 1:  # Major
        major, minor, patch = map(int, base_version.split(".")[:3])
        return f"{major + 1}.0.0"
    elif bump_type == 2:  # Minor
        major, minor, patch = map(int, base_version.split(".")[:3])
        return f"{major}.{minor + 1}.0"
    elif bump_type == 3:  # Patch
        major, minor, patch = map(int, base_version.split(".")[:3])
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
@option(
    "--sync-versions",
    is_flag=True,
    help="Sync all packages to the same version (uses qdrant-loader as source of truth)",
)
def release(dry_run: bool = False, verbose: bool = False, sync_versions: bool = False):
    """Create a new release with unified versioning for all packages.

    All packages will always have the same version number. The qdrant-loader
    package is used as the source of truth for the current version.
    """
    # Setup logging
    logger = setup_logging(verbose)

    # Handle version sync if requested
    if sync_versions:
        print("🔄 SYNCING PACKAGE VERSIONS")
        print("─" * 40)

        # Get the source version from qdrant-loader
        source_version = get_package_version("qdrant-loader")
        print(f"Using qdrant-loader version as source: {source_version}")

        if dry_run:
            print("\n[DRY RUN] Would sync all packages to this version:")
            for package_name in PACKAGES.keys():
                current_ver = get_package_version(package_name)
                if current_ver != source_version:
                    print(f"   • {package_name}: {current_ver} → {source_version}")
                else:
                    print(f"   • {package_name}: {current_ver} (already synced)")
        else:
            print("\nSyncing packages...")
            sync_all_package_versions(source_version, dry_run)
            run_command("git add packages/*/pyproject.toml", dry_run)
            run_command(
                f'git commit -m "chore: sync all packages to version {source_version}"',
                dry_run,
            )
            print("✅ All packages synced successfully!")

        return

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Run safety checks and collect results in dry run mode
    check_results = {}
    check_results["git_status"] = check_git_status(dry_run)
    check_results["current_branch"] = check_current_branch(dry_run)
    check_results["unpushed_commits"] = check_unpushed_commits(dry_run)
    check_results["main_up_to_date"] = check_main_up_to_date(dry_run)
    check_results["github_workflows"] = check_github_workflows(dry_run)

    # In dry run mode, show summary of all checks
    if dry_run:
        print("📋 SAFETY CHECKS")
        print("─" * 50)

        failed_checks = []
        for check_name, passed in check_results.items():
            status = "✅" if passed else "❌"
            check_display_name = check_name.replace("_", " ").title()
            print(f"{status} {check_display_name}")
            if not passed:
                failed_checks.append(check_display_name)

        if failed_checks:
            print(f"\n⚠️  {len(failed_checks)} issue(s) need to be fixed:")
            for check in failed_checks:
                print(f"   • {check}")
            print("\n💡 Continuing to show what would happen after fixes...\n")
        else:
            print("\n✅ All checks passed!\n")
    else:
        # In real mode, exit if any check failed
        if not all(check_results.values()):
            logger.error("One or more safety checks failed. Aborting release.")
            sys.exit(1)

    current_versions = get_all_package_versions()
    current_version = get_current_version()

    # Display current version
    if not dry_run:
        print(f"\n📦 CURRENT VERSION: {current_version}")
        print("─" * 30)
        print("All packages use the same version:")

    # Get new version strategy
    if not dry_run:
        print("\n🔢 VERSION BUMP OPTIONS")
        print("─" * 30)
        print("1. Major (e.g., 1.0.0)")
        print("2. Minor (e.g., 0.2.0)")
        print("3. Patch (e.g., 0.1.4)")
        print("4. Beta (e.g., 0.1.3b2)")
        print("5. Custom")

    if dry_run:
        # In dry run mode, use patch version bump as default example
        choice = 3
        custom_version = None
        print("🔢 VERSION CHANGE (using patch bump as example)")
        print("─" * 50)
    else:
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

    # Calculate new version (same for all packages)
    new_version = calculate_new_version(current_version, choice, custom_version)

    # Apply the same version to all packages
    new_versions = {}
    for package_name in PACKAGES.keys():
        new_versions[package_name] = new_version

    # Display planned change
    print(f"All packages: {current_version} → {new_version}")

    if dry_run:
        print("\n🚀 PLANNED RELEASE ACTIONS")
        print("─" * 50)

        print("\n1️⃣  Create and push tags:")
        for package_name in PACKAGES.keys():
            tag_name = f"{package_name}-v{current_version}"
            print(f"   • {tag_name}")
        print("   • Push all tags to GitHub")

        print("\n2️⃣  Create GitHub releases:")
        for package_name in PACKAGES.keys():
            print(f"   • {package_name} v{current_version}")

        print("\n3️⃣  Update package versions:")
        print(f"   • All packages: {current_version} → {new_version}")

        print("\n4️⃣  Commit changes:")
        print("   • Stage updated pyproject.toml files")
        print("   • Create commit: 'chore(release): bump versions'")

        print("\n" + "─" * 50)

        if failed_checks:
            print("⚠️  NEXT STEPS")
            print(f"   Fix {len(failed_checks)} issue(s) before running the release:")
            for check in failed_checks:
                print(f"   • {check}")
            print("\n   Then run: python release.py")
        else:
            print("✅ READY TO RELEASE")
            print("   All checks passed! Run: python release.py")

        return

    # Create and push tags with current version
    for package_name in PACKAGES.keys():
        tag_name = f"{package_name}-v{current_version}"
        run_command(
            f'git tag -a {tag_name} -m "Release {package_name} v{current_version}"',
            dry_run,
        )

    run_command("git push origin main --tags", dry_run)

    # Create GitHub releases with current version
    token = get_github_token(dry_run)
    for package_name in PACKAGES.keys():
        create_github_release(package_name, current_version, token, dry_run)

    # Update versions for all packages
    update_all_package_versions(new_versions, dry_run)

    # Create commit with all version updates
    run_command("git add packages/*/pyproject.toml", dry_run)
    run_command('git commit -m "chore(release): bump versions"', dry_run)

    print("\n🎉 RELEASE COMPLETED SUCCESSFULLY!")
    print("─" * 40)
    print(f"\n📦 Released version: v{current_version}")
    print("   All packages released with the same version")
    print(f"\n🔄 Updated to: v{new_version}")
    print("   All packages now have the same new version")


if __name__ == "__main__":
    release()
