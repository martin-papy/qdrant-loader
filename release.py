#!/usr/bin/env python3

import subprocess
import sys
import re
import tomli
import tomli_w
from pathlib import Path
from typing import Optional
import click
import requests
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(level)  # Explicitly set the level on the logger
    return logger

def get_current_version() -> str:
    """Get the current version from pyproject.toml."""
    logger = logging.getLogger(__name__)
    logger.debug("Reading current version from pyproject.toml")
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    version = pyproject["project"]["version"]
    logger.debug(f"Current version: {version}")
    return version

def update_version(new_version: str, dry_run: bool = False) -> None:
    """Update the version in pyproject.toml."""
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.info(f"[DRY RUN] Would update version in pyproject.toml to {new_version}")
        return
    
    logger.info(f"Updating version in pyproject.toml to {new_version}")
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    
    pyproject["project"]["version"] = new_version
    
    with open("pyproject.toml", "wb") as f:
        tomli_w.dump(pyproject, f)
    logger.debug("Version updated successfully")

def run_command(cmd: str, dry_run: bool = False) -> tuple[str, str]:
    """Run a shell command and return stdout and stderr."""
    logger = logging.getLogger(__name__)
    if dry_run and not cmd.startswith(("git status", "git branch", "git log", "git fetch", "git rev-list", "git remote", "git rev-parse")):
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
        logger.error("There are uncommitted changes. Please commit or stash them first.")
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
        logger.error("There are unpushed commits. Please push all changes before creating a release.")
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

def create_github_release(version: str, token: str, dry_run: bool = False) -> None:
    """Create a GitHub release."""
    logger = logging.getLogger(__name__)
    if dry_run:
        logger.info(f"[DRY RUN] Would create GitHub release for version {version}")
        return
    
    logger.info(f"Creating GitHub release for version {version}")
    # Get the latest commits for release notes
    stdout, _ = run_command("git log --pretty=format:'%h %s' -n 10")
    release_notes = f"## Changes\n\n```\n{stdout}\n```"
    
    # Create release
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "tag_name": f"v{version}",
        "name": f"Release v{version}",
        "body": release_notes,
        "draft": False,
        "prerelease": "b" in version
    }
    
    # Get repository info
    stdout, _ = run_command("git remote get-url origin", dry_run)
    logger.debug(f"Raw Git remote URL: {stdout}")
    
    # Handle both SSH and HTTPS URLs
    if stdout.startswith("https://"):
        # Handle HTTPS URLs (https://github.com/username/repo.git)
        repo_url = stdout.replace("https://", "").replace(".git", "")
    elif stdout.startswith("ssh://"):
        # Handle SSH URLs with ssh:// prefix (ssh://git@github.com/username/repo.git)
        # Remove ssh://git@ and .git, then split by / and take the last two parts
        clean_url = stdout.replace("ssh://git@", "").replace(".git", "")
        parts = clean_url.split("/")
        if len(parts) >= 3:
            repo_url = "/".join(parts[-2:])
        else:
            logger.error(f"Invalid repository URL format: {stdout}")
            sys.exit(1)
    else:
        # Handle SSH URLs without ssh:// prefix (git@github.com:username/repo.git)
        repo_url = stdout.replace("git@", "").replace(":", "/").replace(".git", "")
    
    if not repo_url:
        logger.error("Could not determine repository path from Git remote URL")
        sys.exit(1)
    
    logger.debug(f"Repository URL: {repo_url}")
    
    response = requests.post(
        f"https://api.github.com/repos/{repo_url}/releases",
        headers=headers,
        json=data
    )
    
    if response.status_code != 201:
        logger.error(f"Error creating GitHub release: {response.text}")
        sys.exit(1)
    logger.info("GitHub release created successfully")

def check_main_up_to_date(dry_run: bool = False) -> None:
    """Check if local main branch is up to date with remote main."""
    logger = logging.getLogger(__name__)
    logger.info("Starting main branch up-to-date check...")
    logger.debug("Checking if main branch is up to date")
    stdout, _ = run_command("git fetch origin main", dry_run)
    stdout, _ = run_command("git rev-list HEAD...origin/main --count", dry_run)
    if stdout != "0":
        logger.error("Local main branch is not up to date with remote main. Please pull the latest changes first.")
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
    
    # Handle both SSH and HTTPS URLs
    if stdout.startswith("https://"):
        # Handle HTTPS URLs (https://github.com/username/repo.git)
        repo_url = stdout.replace("https://", "").replace(".git", "")
    elif stdout.startswith("ssh://"):
        # Handle SSH URLs with ssh:// prefix (ssh://git@github.com/username/repo.git)
        # Remove ssh://git@ and .git, then split by / and take the last two parts
        clean_url = stdout.replace("ssh://git@", "").replace(".git", "")
        parts = clean_url.split("/")
        if len(parts) >= 3:
            repo_url = "/".join(parts[-2:])
        else:
            logger.error(f"Invalid repository URL format: {stdout}")
            sys.exit(1)
    else:
        # Handle SSH URLs without ssh:// prefix (git@github.com:username/repo.git)
        repo_url = stdout.replace("git@", "").replace(":", "/").replace(".git", "")
    
    if not repo_url:
        logger.error("Could not determine repository path from Git remote URL")
        sys.exit(1)
    
    logger.debug(f"Repository URL: {repo_url}")
    
    # Get GitHub token
    token = get_github_token(dry_run)
    logger.debug("GitHub token obtained")
    
    # Get the latest workflow runs
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # First check for running workflows
    logger.debug("Checking for running workflows")
    response = requests.get(
        f"https://api.github.com/repos/{repo_url}/actions/runs",
        headers=headers,
        params={"branch": "main", "status": "in_progress", "per_page": 5}
    )
    
    if response.status_code != 200:
        logger.error(f"Error checking GitHub Actions status: {response.text}")
        sys.exit(1)
    
    runs = response.json()["workflow_runs"]
    if runs:
        logger.error("There are workflows still running. Please wait for them to complete.")
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
        params={"branch": "main", "status": "completed", "per_page": 5}
    )
    
    if response.status_code != 200:
        logger.error(f"Error checking GitHub Actions status: {response.text}")
        sys.exit(1)
    
    runs = response.json()["workflow_runs"]
    if not runs:
        logger.error("No recent workflow runs found. Please ensure workflows are running.")
        sys.exit(1)
    
    # Check the most recent run for each workflow
    workflows = {}
    for run in runs:
        workflow_name = run["name"]
        if workflow_name not in workflows:
            workflows[workflow_name] = run
    
    for workflow_name, run in workflows.items():
        if run["conclusion"] != "success":
            logger.error(f"Workflow '{workflow_name}' is not passing. Latest run status: {run['conclusion']}")
            logger.error(f"Please check the workflow run at: {run['html_url']}")
            sys.exit(1)
        
        # Check if the workflow run matches our current commit
        if run["head_sha"] != current_commit:
            logger.error(f"Workflow '{workflow_name}' was run on a different commit. Please ensure all workflows are run on the current commit.")
            logger.error(f"Current commit: {current_commit}")
            logger.error(f"Workflow commit: {run['head_sha']}")
            logger.error(f"Workflow run: {run['html_url']}")
            sys.exit(1)
    
    logger.info("All workflows are passing and match the current commit")
    logger.info("GitHub workflows check completed successfully")

@click.command()
@click.option('--dry-run', is_flag=True, help='Simulate the release process without making any changes')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def release(dry_run: bool, verbose: bool):
    """Create a new release and bump version."""
    # Setup logging
    logger = setup_logging(verbose)
    
    if dry_run:
        logger.info("Running in dry-run mode. No changes will be made, but all safety checks will be performed.")
    
    # Run safety checks
    check_git_status(dry_run)
    check_current_branch(dry_run)
    check_unpushed_commits(dry_run)
    check_main_up_to_date(dry_run)
    check_github_workflows(dry_run)
    
    if dry_run:
        logger.info("All safety checks passed. In a real run, the following changes would be made:")
    
    current_version = get_current_version()
    logger.info(f"Current version: {current_version}")
    
    # Get new version
    logger.info("\nVersion bump options:")
    logger.info("1. Major (e.g., 1.0.0)")
    logger.info("2. Minor (e.g., 0.2.0)")
    logger.info("3. Patch (e.g., 0.1.4)")
    logger.info("4. Beta (e.g., 0.1.3b2)")
    logger.info("5. Custom")
    
    choice = click.prompt("Select version bump type", type=int)
    
    if choice == 1:
        major, minor, patch = map(int, current_version.split(".")[:3])
        new_version = f"{major + 1}.0.0"
    elif choice == 2:
        major, minor, patch = map(int, current_version.split(".")[:3])
        new_version = f"{major}.{minor + 1}.0"
    elif choice == 3:
        major, minor, patch = map(int, current_version.split(".")[:3])
        new_version = f"{major}.{minor}.{patch + 1}"
    elif choice == 4:
        if "b" in current_version:
            base_version, beta_num = current_version.split("b")
            new_version = f"{base_version}b{int(beta_num) + 1}"
        else:
            new_version = f"{current_version}b1"
    elif choice == 5:
        new_version = click.prompt("Enter new version")
    else:
        logger.error("Invalid choice")
        sys.exit(1)
    
    logger.info(f"Selected new version: {new_version}")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would create and push tag v{current_version}")
        logger.info(f"[DRY RUN] Would create release for version {current_version}")
        logger.info(f"[DRY RUN] Would update version in pyproject.toml to {new_version}")
        logger.info(f"[DRY RUN] Would create commit: chore(release): bump version to v{new_version}")
        return
    
    # Create and push tag with current version
    run_command(f'git tag -a v{current_version} -m "Release v{current_version}"', dry_run)
    run_command("git push origin main --tags", dry_run)
    
    # Create GitHub release with current version
    token = get_github_token(dry_run)
    create_github_release(current_version, token, dry_run)
    
    # Update version
    update_version(new_version, dry_run)
    
    # Create commit
    run_command(f'git commit -am "chore(release): bump version to v{new_version}"', dry_run)
    
    logger.info(f"\nSuccessfully created release v{current_version} and bumped version to v{new_version}!")

if __name__ == "__main__":
    release() 