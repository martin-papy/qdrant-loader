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
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_current_version() -> str:
    """Get the current version from pyproject.toml."""
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    return pyproject["project"]["version"]

def update_version(new_version: str, dry_run: bool = False) -> None:
    """Update the version in pyproject.toml."""
    if dry_run:
        click.echo(f"[DRY RUN] Would update version in pyproject.toml to {new_version}")
        return
    
    with open("pyproject.toml", "rb") as f:
        pyproject = tomli.load(f)
    
    pyproject["project"]["version"] = new_version
    
    with open("pyproject.toml", "wb") as f:
        tomli_w.dump(pyproject, f)

def run_command(cmd: str, dry_run: bool = False) -> tuple[str, str]:
    """Run a shell command and return stdout and stderr."""
    if dry_run:
        click.echo(f"[DRY RUN] Would execute: {cmd}")
        return "", ""
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

def check_git_status(dry_run: bool = False) -> None:
    """Check if the working directory is clean."""
    if dry_run:
        click.echo("[DRY RUN] Would check git status")
        return
    
    stdout, _ = run_command("git status --porcelain")
    if stdout:
        click.echo("Error: There are uncommitted changes. Please commit or stash them first.")
        sys.exit(1)

def check_current_branch(dry_run: bool = False) -> None:
    """Check if we're on the main branch."""
    if dry_run:
        click.echo("[DRY RUN] Would check current branch")
        return
    
    stdout, _ = run_command("git branch --show-current")
    if stdout != "main":
        click.echo("Error: Not on main branch. Please switch to main branch first.")
        sys.exit(1)

def check_unpushed_commits(dry_run: bool = False) -> None:
    """Check if there are any unpushed commits."""
    if dry_run:
        click.echo("[DRY RUN] Would check for unpushed commits")
        return
    
    stdout, _ = run_command("git log origin/main..HEAD")
    if stdout:
        click.echo("Error: There are unpushed commits. Please push all changes before creating a release.")
        sys.exit(1)
    # If we get here, it means all commits are pushed, which is what we want for a release

def get_github_token(dry_run: bool = False) -> str:
    """Get GitHub token from environment variable."""
    if dry_run:
        click.echo("[DRY RUN] Would check for GITHUB_TOKEN")
        return "dry-run-token"
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        click.echo("Error: GITHUB_TOKEN not found in .env file.")
        sys.exit(1)
    return token

def create_github_release(version: str, token: str, dry_run: bool = False) -> None:
    """Create a GitHub release."""
    if dry_run:
        click.echo(f"[DRY RUN] Would create GitHub release for version {version}")
        return
    
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
    stdout, _ = run_command("git remote get-url origin")
    repo_url = stdout.split(":")[1].replace(".git", "")
    
    response = requests.post(
        f"https://api.github.com/repos/{repo_url}/releases",
        headers=headers,
        json=data
    )
    
    if response.status_code != 201:
        click.echo(f"Error creating GitHub release: {response.text}")
        sys.exit(1)

def check_main_up_to_date(dry_run: bool = False) -> None:
    """Check if local main branch is up to date with remote main."""
    if dry_run:
        click.echo("[DRY RUN] Would check if main is up to date with remote")
        return
    
    stdout, _ = run_command("git fetch origin main")
    stdout, _ = run_command("git rev-list HEAD...origin/main --count")
    if stdout != "0":
        click.echo("Error: Local main branch is not up to date with remote main. Please pull the latest changes first.")
        sys.exit(1)

def check_github_workflows(dry_run: bool = False) -> None:
    """Check if all GitHub Actions workflows are passing."""
    if dry_run:
        click.echo("[DRY RUN] Would check GitHub Actions workflow status")
        return
    
    # Get repository info
    stdout, _ = run_command("git remote get-url origin")
    repo_url = stdout.split(":")[1].replace(".git", "")
    
    # Get GitHub token
    token = get_github_token(dry_run)
    
    # Get the latest workflow runs
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(
        f"https://api.github.com/repos/{repo_url}/actions/runs",
        headers=headers,
        params={"branch": "main", "status": "completed", "per_page": 5}
    )
    
    if response.status_code != 200:
        click.echo(f"Error checking GitHub Actions status: {response.text}")
        sys.exit(1)
    
    runs = response.json()["workflow_runs"]
    if not runs:
        click.echo("Error: No recent workflow runs found. Please ensure workflows are running.")
        sys.exit(1)
    
    # Check the most recent run for each workflow
    workflows = {}
    for run in runs:
        workflow_name = run["name"]
        if workflow_name not in workflows:
            workflows[workflow_name] = run
    
    for workflow_name, run in workflows.items():
        if run["conclusion"] != "success":
            click.echo(f"Error: Workflow '{workflow_name}' is not passing. Latest run status: {run['conclusion']}")
            click.echo(f"Please check the workflow run at: {run['html_url']}")
            sys.exit(1)

@click.command()
@click.option('--dry-run', is_flag=True, help='Simulate the release process without making any changes')
def release(dry_run: bool):
    """Create a new release and bump version."""
    if dry_run:
        click.echo("Running in dry-run mode. No changes will be made.")
    
    # Run safety checks
    check_git_status(dry_run)
    check_current_branch(dry_run)
    check_unpushed_commits(dry_run)
    check_main_up_to_date(dry_run)
    check_github_workflows(dry_run)
    
    current_version = get_current_version()
    click.echo(f"Current version: {current_version}")
    
    # Get new version
    click.echo("\nVersion bump options:")
    click.echo("1. Major (e.g., 1.0.0)")
    click.echo("2. Minor (e.g., 0.2.0)")
    click.echo("3. Patch (e.g., 0.1.4)")
    click.echo("4. Beta (e.g., 0.1.3b2)")
    click.echo("5. Custom")
    
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
        click.echo("Invalid choice")
        sys.exit(1)
    
    # Update version
    update_version(new_version, dry_run)
    
    # Create commit
    run_command(f'git commit -am "chore(release): bump version to v{new_version}"', dry_run)
    
    # Create and push tag
    run_command(f'git tag -a v{new_version} -m "Release v{new_version}"', dry_run)
    run_command("git push origin main --tags", dry_run)
    
    # Create GitHub release
    token = get_github_token(dry_run)
    create_github_release(new_version, token, dry_run)
    
    click.echo(f"\n{'[DRY RUN] Would ' if dry_run else ''}Successfully created release v{new_version}!")

if __name__ == "__main__":
    release() 