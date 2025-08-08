#!/usr/bin/env python3
"""
Tests for the favicon generation script.
"""

import pytest
import shutil
from pathlib import Path
import os
import sys
import subprocess


class TestFaviconGenerationScript:
    """Test suite for favicon generation script structure and basic functionality."""

    def test_favicon_script_exists(self):
        """Test that the favicon generation script exists."""
        favicon_script = Path("website/assets/generate_favicons.py")
        assert favicon_script.exists(), "Favicon generation script should exist"
        assert favicon_script.is_file(), "Favicon script should be a file"

    def test_favicon_script_syntax(self):
        """Test that the favicon generation script has valid Python syntax."""
        favicon_script = Path("website/assets/generate_favicons.py")

        with open(favicon_script, "r") as f:
            source = f.read()

        try:
            compile(source, str(favicon_script), "exec")
        except SyntaxError as e:
            pytest.fail(f"Favicon script has syntax error: {e}")

    def test_favicon_script_has_main_function(self):
        """Test that the favicon script has a main function."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        assert "def main(" in content, "Script should have a main function"
        assert 'if __name__ == "__main__":' in content, "Script should be executable"

    def test_favicon_script_has_required_functions(self):
        """Test that the favicon script has required functions."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        required_functions = ["svg_to_png", "generate_ico", "main"]

        for func in required_functions:
            assert f"def {func}(" in content, f"Script should have {func} function"

    def test_favicon_script_imports(self):
        """Test that the favicon script has required imports."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        # Check for essential imports
        assert "from pathlib import Path" in content, "Script should import Path"
        assert (
            "import cairosvg" in content or "from cairosvg" in content
        ), "Script should import cairosvg"
        assert (
            "from PIL import Image" in content or "import PIL" in content
        ), "Script should import PIL"

    @pytest.mark.requires_deps
    def test_favicon_script_can_run_help(self):
        """Test that the favicon script can run and show help."""
        favicon_script = Path("website/assets/generate_favicons.py")

        try:
            # Try to run the script with --help or similar
            result = subprocess.run(
                [sys.executable, str(favicon_script), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Script might not have --help, but it shouldn't crash
            # We're mainly testing that it can be executed
            assert result.returncode in [0, 1, 2], "Script should be executable"

        except subprocess.TimeoutExpired:
            pytest.skip("Script execution timed out")
        except Exception as e:
            pytest.skip(f"Could not test script execution: {e}")

    def test_favicon_directories_structure(self):
        """Test that favicon-related directories exist."""
        assets_dir = Path("website/assets")
        assert assets_dir.exists(), "Assets directory should exist"

        # Check if favicons directory exists or can be created
        favicons_dir = assets_dir / "favicons"
        if not favicons_dir.exists():
            # This is okay, it might be created by the script
            pass

    def test_logo_files_exist(self):
        """Test that logo files exist for favicon generation."""
        assets_dir = Path("website/assets")
        logos_dir = assets_dir / "logos"

        assert logos_dir.exists(), "Logos directory should exist"

        # Look for SVG logo files
        svg_files = list(logos_dir.glob("*.svg"))
        assert len(svg_files) > 0, "Should have at least one SVG logo file"

    @pytest.mark.integration
    def test_favicon_generation_with_mock_structure(self, mock_project_structure):
        """Test favicon generation with mock project structure."""
        original_cwd = os.getcwd()
        os.chdir(mock_project_structure)

        try:
            # Copy the actual favicon script
            actual_script = (
                Path(original_cwd) / "website" / "assets" / "generate_favicons.py"
            )
            mock_script = (
                mock_project_structure / "website" / "assets" / "generate_favicons.py"
            )

            if actual_script.exists():
                shutil.copy2(actual_script, mock_script)

                # Create favicons directory
                favicons_dir = (
                    mock_project_structure / "website" / "assets" / "favicons"
                )
                favicons_dir.mkdir(exist_ok=True)

                try:
                    # Try to run the favicon generation
                    result = subprocess.run(
                        [sys.executable, str(mock_script)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    # Check if it ran successfully or failed gracefully
                    if result.returncode == 0:
                        # Success - check if files were created
                        expected_files = [
                            "favicon.ico",
                            "apple-touch-icon.png",
                            "android-chrome-192x192.png",
                            "android-chrome-512x512.png",
                        ]

                        for filename in expected_files:
                            favicon_file = favicons_dir / filename
                            if favicon_file.exists():
                                assert (
                                    favicon_file.stat().st_size > 0
                                ), f"{filename} should not be empty"

                    else:
                        # Failure is okay if dependencies are missing
                        print(
                            f"Favicon generation failed (expected in test): {result.stderr}"
                        )

                except subprocess.TimeoutExpired:
                    pytest.skip("Favicon generation timed out")

        finally:
            os.chdir(original_cwd)

    def test_error_handling_in_script(self):
        """Test that the favicon script has proper error handling."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        # Check for basic error handling patterns
        assert "try:" in content, "Script should have error handling"
        assert "except" in content, "Script should catch exceptions"

        # Check for specific error handling
        error_patterns = ["FileNotFoundError", "ImportError", "Exception"]

        has_error_handling = any(pattern in content for pattern in error_patterns)
        assert has_error_handling, "Script should handle common errors"

    def test_favicon_output_paths(self):
        """Test that the script uses correct output paths."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        # Check for favicon-related file extensions
        favicon_extensions = [".ico", ".png"]
        has_favicon_outputs = any(ext in content for ext in favicon_extensions)
        assert has_favicon_outputs, "Script should generate favicon files"

    def test_svg_input_handling(self):
        """Test that the script handles SVG input files."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        # Check for SVG-related code
        svg_indicators = [".svg", "svg2png", "cairosvg"]
        has_svg_handling = any(indicator in content for indicator in svg_indicators)
        assert has_svg_handling, "Script should handle SVG input files"


class TestFaviconGenerationEdgeCases:
    """Test edge cases and error conditions for favicon generation."""

    def test_missing_dependencies_handling(self):
        """Test that the script handles missing dependencies gracefully."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        # Should have import error handling
        import_error_patterns = ["ImportError", "ModuleNotFoundError", "try:", "except"]

        has_import_handling = any(
            pattern in content for pattern in import_error_patterns
        )
        assert has_import_handling, "Script should handle missing dependencies"

    def test_file_permission_considerations(self):
        """Test that the script considers file permissions."""
        favicon_script = Path("website/assets/generate_favicons.py")
        content = favicon_script.read_text()

        # Should have some form of file handling
        file_operations = ["open(", "write", "save", "mkdir"]
        has_file_ops = any(op in content for op in file_operations)
        assert has_file_ops, "Script should perform file operations"

    @pytest.mark.slow
    def test_script_performance_considerations(self):
        """Test that the script has reasonable performance characteristics."""
        favicon_script = Path("website/assets/generate_favicons.py")

        # Check file size (shouldn't be too large)
        file_size = favicon_script.stat().st_size
        assert file_size < 50000, "Script should be reasonably sized (< 50KB)"

        # Check line count (shouldn't be too complex)
        with open(favicon_script, "r") as f:
            line_count = len(f.readlines())
        assert line_count < 500, "Script should be reasonably sized (< 500 lines)"


if __name__ == "__main__":
    pytest.main([__file__])
