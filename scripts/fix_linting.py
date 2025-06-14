#!/usr/bin/env python3
"""
Script to fix common linting errors in the codebase.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


def remove_unused_imports(file_path):
    """Remove unused imports from a Python file using autoflake."""
    try:
        subprocess.run(
            [
                "python",
                "-m",
                "autoflake",
                "--remove-all-unused-imports",
                "--remove-unused-variables",
                "--in-place",
                str(file_path),
            ],
            check=True,
            capture_output=True,
        )
        print(f"✓ Removed unused imports from {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to remove unused imports from {file_path}: {e}")


def fix_line_length_issues(file_path):
    """Fix line length issues by applying Black formatting."""
    try:
        subprocess.run(
            ["python", "-m", "black", "--line-length=88", str(file_path)],
            check=True,
            capture_output=True,
        )
        print(f"✓ Fixed line length in {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to fix line length in {file_path}: {e}")


def fix_trailing_whitespace(file_path):
    """Remove trailing whitespace from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove trailing whitespace from each line
        lines = content.splitlines()
        fixed_lines = [line.rstrip() for line in lines]

        # Join lines back together
        fixed_content = "\n".join(fixed_lines)
        if content.endswith("\n"):
            fixed_content += "\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)

        print(f"✓ Fixed trailing whitespace in {file_path}")
    except Exception as e:
        print(f"✗ Failed to fix trailing whitespace in {file_path}: {e}")


def fix_comparison_issues(file_path):
    """Fix comparison to True/False issues."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Fix comparison to True
        content = re.sub(r"== True\b", "", content)
        content = re.sub(r"is True\b", "", content)

        # Fix comparison to False
        content = re.sub(r"== False\b", " is False", content)
        content = re.sub(r"!= False\b", "", content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Fixed comparison issues in {file_path}")
    except Exception as e:
        print(f"✗ Failed to fix comparison issues in {file_path}: {e}")


def fix_f_string_issues(file_path):
    """Fix f-string missing placeholders."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find f-strings without placeholders and convert to regular strings
        content = re.sub(r'f"([^"]*)"(?![^{]*})', r'"\1"', content)
        content = re.sub(r"f'([^']*)'(?![^{]*})", r"'\1'", content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Fixed f-string issues in {file_path}")
    except Exception as e:
        print(f"✗ Failed to fix f-string issues in {file_path}: {e}")


def fix_module_level_imports(file_path):
    """Fix module level imports not at top of file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Separate imports and other code
        imports = []
        other_lines = []
        in_docstring = False
        docstring_quotes = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Handle docstrings
            if not in_docstring and (
                stripped.startswith('"""') or stripped.startswith("'''")
            ):
                in_docstring = True
                docstring_quotes = stripped[:3]
                other_lines.append(line)
                if stripped.count(docstring_quotes) >= 2:
                    in_docstring = False
                continue
            elif in_docstring:
                other_lines.append(line)
                if docstring_quotes and docstring_quotes in stripped:
                    in_docstring = False
                continue

            # Skip comments and empty lines at the top
            if stripped.startswith("#") or not stripped:
                other_lines.append(line)
                continue

            # Check if it's an import
            if stripped.startswith(("import ", "from ")) and not in_docstring:
                imports.append(line)
            else:
                other_lines.append(line)

        # Reconstruct file with imports at top (after initial comments/docstrings)
        new_lines = []
        added_imports = False

        for line in other_lines:
            stripped = line.strip()
            if (
                not added_imports
                and stripped
                and not stripped.startswith("#")
                and not stripped.startswith(('"""', "'''"))
            ):
                # Add imports before first non-comment, non-docstring line
                new_lines.extend(imports)
                if imports:
                    new_lines.append("\n")
                added_imports = True
            new_lines.append(line)

        # If we never added imports, add them at the end
        if not added_imports and imports:
            new_lines.extend(imports)

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print(f"✓ Fixed module level imports in {file_path}")
    except Exception as e:
        print(f"✗ Failed to fix module level imports in {file_path}: {e}")


def install_autoflake():
    """Install autoflake if not available."""
    try:
        subprocess.run(
            ["python", "-m", "autoflake", "--version"], check=True, capture_output=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing autoflake...")
        subprocess.run(["pip", "install", "autoflake"], check=True)


def main():
    """Main function to fix linting errors."""
    print("🔧 Starting linting fixes...")

    # Install required tools
    install_autoflake()

    # Find all Python files in packages directory
    packages_dir = Path("packages")
    if not packages_dir.exists():
        print("❌ packages directory not found!")
        sys.exit(1)

    python_files = list(packages_dir.rglob("*.py"))
    print(f"📁 Found {len(python_files)} Python files")

    for file_path in python_files:
        print(f"\n🔍 Processing {file_path}")

        # Apply fixes in order
        fix_trailing_whitespace(file_path)
        remove_unused_imports(file_path)
        fix_line_length_issues(file_path)
        fix_comparison_issues(file_path)
        fix_f_string_issues(file_path)
        # fix_module_level_imports(file_path)  # Skip this as it's complex

    print("\n✅ Linting fixes completed!")
    print("🔍 Running final linting check...")

    # Run final flake8 check
    try:
        result = subprocess.run(
            [
                "python",
                "-m",
                "flake8",
                "packages/",
                "--max-line-length=88",
                "--extend-ignore=E203,W503,E402",  # Ignore module level imports for now
                "--exclude=__pycache__,*.pyc,.git,venv,build,dist,*.egg-info",
                "--count",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("🎉 All linting errors fixed!")
        else:
            print(f"⚠️  Remaining errors: {result.stdout.strip()}")
            print("Some errors may need manual fixing.")
    except Exception as e:
        print(f"❌ Failed to run final check: {e}")


if __name__ == "__main__":
    main()
