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
    "qdrant-loader-workspace": {
        "path": ".",
        "pyproject": "pyproject.toml",
        "create_release": False,  # Workspace config, no need for GitHub release
    },
    "qdrant-loader": {
        "path": "packages/qdrant-loader",
        "pyproject": "packages/qdrant-loader/pyproject.toml",
        "create_release": True,
    },
    "qdrant-loader-mcp-server": {
        "path": "packages/qdrant-loader-mcp-server",
        "pyproject": "packages/qdrant-loader-mcp-server/pyproject.toml",
        "create_release": True,
    },
}


def get_packages_for_release() -> list[str]:
    """Get packages that need releases in the correct order.

    Returns packages in order where qdrant-loader is LAST,
    ensuring it appears as the latest release in GitHub.
    """
    packages_to_release = [
        name for name, info in PACKAGES.items() if info.get("create_release", True)
    ]

    # Ensure qdrant-loader is last (will be the latest release)
    if "qdrant-loader" in packages_to_release:
        packages_to_release.remove("qdrant-loader")
        packages_to_release.append("qdrant-loader")

    return packages_to_release


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
            "❌ Version mismatch detected! All packages should have the same version."
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
    logging.getLogger(__name__)
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


def check_release_notes_updated(new_version: str, dry_run: bool = False) -> bool:
    """Check if RELEASE_NOTES.md has been updated with the new version."""
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Checking if RELEASE_NOTES.md has been updated for version {new_version}"
    )

    release_notes_path = Path("RELEASE_NOTES.md")
    if not release_notes_path.exists():
        logger.error("RELEASE_NOTES.md file not found in the repository root")
        if not dry_run:
            sys.exit(1)
        return False

    try:
        with open(release_notes_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for the version section at the beginning of the file
        # Expected format: ## Version X.Y.Z - Date
        import re

        # Extract the first version section after the title
        lines = content.split("\n")
        version_pattern = r"^## Version (\d+\.\d+\.\d+(?:b\d+)?)"

        for line in lines:
            if line.startswith("## Version"):
                match = re.match(version_pattern, line)
                if match:
                    found_version = match.group(1)
                    logger.debug(
                        f"Found version section in RELEASE_NOTES.md: {found_version}"
                    )

                    if found_version == new_version:
                        logger.debug(
                            "Release notes are up to date with the new version"
                        )
                        return True
                    else:
                        logger.error(
                            f"RELEASE_NOTES.md has not been updated for version {new_version}"
                        )
                        logger.error(
                            f"Found version {found_version} but expected {new_version}"
                        )
                        logger.error(
                            "Please add a release notes section for the new version at the top of RELEASE_NOTES.md"
                        )
                        logger.error(
                            f"Expected format: ## Version {new_version} - <Date>"
                        )
                        if not dry_run:
                            sys.exit(1)
                        return False
                break

        # If we get here, no version section was found
        logger.error("No version section found in RELEASE_NOTES.md")
        logger.error(f"Please add a release notes section for version {new_version}")
        logger.error(f"Expected format: ## Version {new_version} - <Date>")
        if not dry_run:
            sys.exit(1)
        return False

    except Exception as e:
        logger.error(f"Error reading RELEASE_NOTES.md: {e}")
        if not dry_run:
            sys.exit(1)
        return False


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

    response = requests.get(
        f"https://api.github.com/repos/{repo_url}/actions/runs",
        headers=headers,
        params={"branch": "main", "status": "in_progress", "per_page": 5},
    )

    if response.status_code != 200:
        logger.error(f"Error checking GitHub Actions status: {response.text}")
        if not dry_run:
            sys.exit(1)
        return False

    runs = response.json()["workflow_runs"]
    if runs:
        logger.error(
            "There are workflows still running. Please wait for them to complete."
        )
        for run in runs:
            logger.error(f"- {run['name']} is running: {run['html_url']}")
        if not dry_run:
            sys.exit(1)
        return False

    # Get current commit hash
    current_commit, _ = run_command("git rev-parse HEAD", dry_run)
    logger.debug(f"Current commit hash: {current_commit}")

    # Then check completed workflows
    logger.debug("Checking completed workflows")
    response = requests.get(
        f"https://api.github.com/repos/{repo_url}/actions/runs",
        headers=headers,
        params={"branch": "main", "status": "completed", "per_page": 10},
    )

    if response.status_code != 200:
        logger.error(f"Error checking GitHub Actions status: {response.text}")
        if not dry_run:
            sys.exit(1)
        return False

    runs = response.json()["workflow_runs"]
    if not runs:
        logger.error(
            "No recent workflow runs found. Please ensure workflows are running."
        )
        if not dry_run:
            sys.exit(1)
        return False

    # Check the most recent run for each workflow
    workflows = {}
    for run in runs:
        workflow_name = run["name"]
        if workflow_name not in workflows:
            workflows[workflow_name] = run

    # Define workflows that should be excluded from strict commit matching
    # These are typically scheduled workflows or external workflows
    excluded_workflows = {"Scheduled", "Dependabot"}

    # Define critical workflows that must pass and match current commit
    critical_workflows = {"Test and Coverage", "Push on main", "PR"}

    for workflow_name, run in workflows.items():
        if run["conclusion"] != "success":
            logger.error(
                f"Workflow '{workflow_name}' is not passing. Latest run status: {run['conclusion']}"
            )
            logger.error(f"Please check the workflow run at: {run['html_url']}")
            if not dry_run:
                sys.exit(1)
            return False

        # Check if the workflow run matches our current commit
        # Skip this check for excluded workflows (like scheduled ones)
        if workflow_name in excluded_workflows:
            logger.debug(
                f"Skipping commit check for excluded workflow: {workflow_name}"
            )
            continue

        if run["head_sha"] != current_commit:
            # For critical workflows, this is an error
            if workflow_name in critical_workflows:
                logger.error(
                    f"Critical workflow '{workflow_name}' was run on a different commit. Please ensure it runs on the current commit."
                )
                logger.error(f"Current commit: {current_commit}")
                logger.error(f"Workflow commit: {run['head_sha']}")
                logger.error(f"Workflow run: {run['html_url']}")
                if not dry_run:
                    sys.exit(1)
                return False
            else:
                # For non-critical workflows, just log a warning
                logger.debug(
                    f"Non-critical workflow '{workflow_name}' was run on a different commit (this is acceptable)"
                )
                logger.debug(f"Current commit: {current_commit}")
                logger.debug(f"Workflow commit: {run['head_sha']}")

    logger.info("All critical workflows are passing and match the current commit")
    logger.info("GitHub workflows check completed successfully")
    return True


def calculate_new_version(
    current_version: str, bump_type: int, custom_version: str | None = None
) -> str:
    """Calculate new version based on bump type."""
    if bump_type == 5 and custom_version is not None:
        # Validate custom version format
        import re

        version_pattern = r"^\d+\.\d+\.\d+(?:b\d+)?$"
        if not re.match(version_pattern, custom_version):
            raise ValueError(
                f"Invalid version format: {custom_version}. Expected format: X.Y.Z or X.Y.Zb<num>"
            )
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


def get_development_status_classifier(version: str) -> str:
    """
    Determine the appropriate Development Status classifier based on version.

    Rules:
    - Any version with 'a' (alpha): "3 - Alpha"
    - Any version with 'b' (beta): "4 - Beta"
    - Any version with 'rc' (release candidate): "4 - Beta"
    - Everything else: "5 - Production/Stable"
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Determining development status for version: {version}")

    version_lower = version.lower()

    if "a" in version_lower:
        status = "Development Status :: 3 - Alpha"
        logger.debug(f"Alpha version detected: {status}")
        return status
    elif "b" in version_lower or "rc" in version_lower:
        status = "Development Status :: 4 - Beta"
        logger.debug(f"Beta/RC version detected: {status}")
        return status
    else:
        status = "Development Status :: 5 - Production/Stable"
        logger.debug(f"Stable version detected: {status}")
        return status


def update_development_status_classifier(
    package_name: str, version: str, dry_run: bool = False
) -> None:
    """Update the Development Status classifier in a package's pyproject.toml."""
    logger = logging.getLogger(__name__)
    pyproject_path = PACKAGES[package_name]["pyproject"]

    # Determine the correct classifier
    new_classifier = get_development_status_classifier(version)

    if dry_run:
        logger.info(
            f"[DRY RUN] Would update Development Status classifier in {pyproject_path} to '{new_classifier}'"
        )
        return

    logger.info(f"Updating Development Status classifier in {pyproject_path}")

    # Read current pyproject.toml
    with open(pyproject_path, "rb") as f:
        pyproject = tomli.load(f)

    # Update the classifier
    if "project" in pyproject and "classifiers" in pyproject["project"]:
        classifiers = pyproject["project"]["classifiers"]

        # Find and replace existing Development Status classifier
        updated = False
        for i, classifier in enumerate(classifiers):
            if classifier.startswith("Development Status ::"):
                old_classifier = classifier
                classifiers[i] = new_classifier
                updated = True
                logger.debug(f"Replaced '{old_classifier}' with '{new_classifier}'")
                break

        # If no Development Status classifier exists, add it
        if not updated:
            classifiers.insert(0, new_classifier)  # Add at the beginning
            logger.debug(f"Added new classifier: '{new_classifier}'")
    else:
        # Create classifiers section if it doesn't exist
        if "project" not in pyproject:
            pyproject["project"] = {}
        pyproject["project"]["classifiers"] = [new_classifier]
        logger.debug(f"Created new classifiers section with: '{new_classifier}'")

    # Write back to file
    with open(pyproject_path, "wb") as f:
        tomli_w.dump(pyproject, f)

    logger.debug(
        f"Development Status classifier updated successfully for {package_name}"
    )


def update_all_development_status_classifiers(
    new_versions: dict[str, str], dry_run: bool = False
) -> None:
    """Update Development Status classifiers for all packages."""
    logger = logging.getLogger(__name__)
    logger.info("Updating Development Status classifiers for all packages")

    for package_name, new_version in new_versions.items():
        update_development_status_classifier(package_name, new_version, dry_run)


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

            print("\n[DRY RUN] Would also update Development Status classifiers:")
            target_classifier = get_development_status_classifier(source_version)
            for package_name in PACKAGES.keys():
                print(f"   • {package_name}: {target_classifier}")
        else:
            print("\nSyncing packages...")
            sync_all_package_versions(source_version, dry_run)

            print("Updating Development Status classifiers...")
            # Create versions dict for classifier update
            sync_versions_dict = {
                package_name: source_version for package_name in PACKAGES.keys()
            }
            update_all_development_status_classifiers(sync_versions_dict, dry_run)

            run_command("git add pyproject.toml packages/*/pyproject.toml", dry_run)
            run_command(
                f'git commit -m "chore: sync all packages to version {source_version} and update classifiers"',
                dry_run,
            )
            print("✅ All packages synced successfully!")

        return

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Run initial safety checks (without release notes check)
    initial_check_results = {}
    initial_check_results["git_status"] = check_git_status(dry_run)
    initial_check_results["current_branch"] = check_current_branch(dry_run)
    initial_check_results["unpushed_commits"] = check_unpushed_commits(dry_run)
    initial_check_results["main_up_to_date"] = check_main_up_to_date(dry_run)
    initial_check_results["github_workflows"] = check_github_workflows(dry_run)

    # In dry run mode, show summary of initial checks
    if dry_run:
        print("📋 INITIAL SAFETY CHECKS")
        print("─" * 50)

        failed_initial_checks = []
        for check_name, passed in initial_check_results.items():
            status = "✅" if passed else "❌"
            check_display_name = check_name.replace("_", " ").title()
            print(f"{status} {check_display_name}")
            if not passed:
                failed_initial_checks.append(check_display_name)

        if failed_initial_checks:
            print(f"\n⚠️  {len(failed_initial_checks)} issue(s) need to be fixed:")
            for check in failed_initial_checks:
                print(f"   • {check}")
            print("\n💡 Continuing to show what would happen after fixes...\n")
        else:
            print("\n✅ All initial checks passed!\n")
    else:
        # In real mode, exit if any initial check failed
        if not all(initial_check_results.values()):
            logger.error("One or more initial safety checks failed. Aborting release.")
            sys.exit(1)

    get_all_package_versions()
    current_version = get_current_version()

    # Display current version
    if not dry_run:
        print(f"\n📦 CURRENT VERSION: {current_version}")
        print("─" * 30)
        print("All packages use the same version:")

    # Get new version strategy
    print("\n🔢 VERSION BUMP OPTIONS")
    print("─" * 30)

    # Calculate and show actual version examples based on current version
    major_version = calculate_new_version(current_version, 1)
    minor_version = calculate_new_version(current_version, 2)
    patch_version = calculate_new_version(current_version, 3)
    beta_version = calculate_new_version(current_version, 4)

    print(f"1. Major ({current_version} → {major_version})")
    print(f"2. Minor ({current_version} → {minor_version})")
    print(f"3. Patch ({current_version} → {patch_version})")
    print(f"4. Beta ({current_version} → {beta_version})")
    print("5. Custom (specify exact version)")

    choice = prompt("Select version bump type", type=int)

    custom_version = None
    if choice == 5:
        print(f"\nCurrent version: {current_version}")
        print("Enter the new version (format: X.Y.Z or X.Y.Zb<num>)")
        print("Examples: 1.2.3, 0.5.0, 2.1.0b1")

        while True:
            custom_version = prompt("New version").strip()
            if not custom_version:
                logger.error("Version cannot be empty")
                continue

            try:
                # Validate the version format using the same logic as calculate_new_version
                import re

                version_pattern = r"^\d+\.\d+\.\d+(?:b\d+)?$"
                if not re.match(version_pattern, custom_version):
                    logger.error(
                        "Invalid version format. Expected format: X.Y.Z or X.Y.Zb<num>"
                    )
                    continue
                break
            except Exception as e:
                logger.error(f"Invalid version: {e}")
                continue

    elif choice not in [1, 2, 3, 4]:
        logger.error("Invalid choice")
        sys.exit(1)

    if dry_run:
        print(
            f"\n🔢 VERSION CHANGE (using {'major' if choice == 1 else 'minor' if choice == 2 else 'patch' if choice == 3 else 'beta' if choice == 4 else 'custom'} bump)"
        )
        print("─" * 50)

    # Calculate new version (same for all packages)
    try:
        new_version = calculate_new_version(current_version, choice, custom_version)
    except ValueError as e:
        logger.error(f"Version calculation failed: {e}")
        sys.exit(1)

    # Now check if release notes have been updated for the new version
    release_notes_check = check_release_notes_updated(new_version, dry_run)

    # Combine all check results
    all_check_results = initial_check_results.copy()
    all_check_results["release_notes_updated"] = release_notes_check

    # Apply the same version to all packages
    new_versions = {}
    for package_name in PACKAGES.keys():
        new_versions[package_name] = new_version

    # Display planned change
    print(f"All packages: {current_version} → {new_version}")

    # Show release notes check result
    if dry_run:
        print("\n📋 RELEASE NOTES CHECK")
        print("─" * 30)
        status = "✅" if release_notes_check else "❌"
        print(f"{status} Release Notes Updated")
        if not release_notes_check:
            print(
                f"   ⚠️  RELEASE_NOTES.md needs to be updated for version {new_version}"
            )
        print()

    if dry_run:
        print("\n🚀 PLANNED RELEASE ACTIONS")
        print("─" * 50)

        print("\n1️⃣  Create and push tags:")
        for package_name in get_packages_for_release():
            tag_name = f"{package_name}-v{current_version}"
            print(f"   • {tag_name}")
        print("   • Push all tags to GitHub")

        print("\n2️⃣  Create GitHub releases:")
        for package_name in get_packages_for_release():
            print(f"   • {package_name} v{current_version}")

        print("\n3️⃣  Update package versions and classifiers:")
        print(f"   • All packages: {current_version} → {new_version}")

        # Show classifier updates
        for package_name in PACKAGES.keys():
            current_classifier = get_development_status_classifier(current_version)
            new_classifier = get_development_status_classifier(new_version)
            if current_classifier != new_classifier:
                print(f"   • {package_name}: {current_classifier} → {new_classifier}")
            else:
                print(f"   • {package_name}: {new_classifier} (no change)")

        print("\n4️⃣  Commit changes:")
        print("   • Stage updated pyproject.toml files")
        print(
            "   • Create commit: 'chore(release): bump versions and update classifiers'"
        )
        print("   • Push new version to remote repository")

        print("\n" + "─" * 50)

        # Check all results including release notes
        all_failed_checks = []
        for check_name, passed in all_check_results.items():
            if not passed:
                check_display_name = check_name.replace("_", " ").title()
                all_failed_checks.append(check_display_name)

        if all_failed_checks:
            print("⚠️  NEXT STEPS")
            print(
                f"   Fix {len(all_failed_checks)} issue(s) before running the release:"
            )
            for check in all_failed_checks:
                print(f"   • {check}")
            print("\n   Then run: python release.py")
        else:
            print("✅ READY TO RELEASE")
            print("   All checks passed! Run: python release.py")

        return

    # In real mode, exit if any check failed (including release notes)
    if not all(all_check_results.values()):
        logger.error("One or more safety checks failed. Aborting release.")
        sys.exit(1)

    # Update versions for all packages FIRST
    update_all_package_versions(new_versions, dry_run)

    # Update Development Status classifiers for all packages
    update_all_development_status_classifiers(new_versions, dry_run)

    # Create commit with all version and classifier updates
    run_command("git add pyproject.toml packages/*/pyproject.toml", dry_run)
    run_command(
        'git commit -m "chore(release): bump versions and update classifiers"', dry_run
    )

    # Push the new version commit to remote
    run_command("git push origin main", dry_run)

    # Create and push tags with NEW version (after version bump)
    for package_name in get_packages_for_release():
        tag_name = f"{package_name}-v{new_version}"  # Use new_version instead of current_version
        run_command(
            f'git tag -a {tag_name} -m "Release {package_name} v{new_version}"',
            dry_run,
        )

    run_command("git push origin main --tags", dry_run)

    # Create GitHub releases with NEW version
    token = get_github_token(dry_run)
    for package_name in get_packages_for_release():
        create_github_release(
            package_name, new_version, token, dry_run
        )  # Use new_version

    print("\n🎉 RELEASE COMPLETED SUCCESSFULLY!")
    print("─" * 40)
    print(f"\n📦 Released version: v{new_version}")  # Show new_version
    print("   All packages released with the same version")
    print(f"\n🔄 Updated from: v{current_version}")  # Show what we updated from
    print("   All packages now have the same new version")
    print("   Development Status classifiers updated automatically")
    print("   New version committed and pushed to remote repository")


if __name__ == "__main__":
    release()
