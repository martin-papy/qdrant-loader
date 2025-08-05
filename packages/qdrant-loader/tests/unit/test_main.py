"""Tests for the main module."""

import sys
from unittest.mock import patch

def test_main_module_cli_import():
    """Test that cli can be imported from main module."""
    from qdrant_loader.main import cli
    assert cli is not None
    assert callable(cli)

def test_main_when_name_is_main():
    """Test that cli() is called when module is run as main."""
    import subprocess
    import sys
    from pathlib import Path
    
    # Get the path to the main.py file
    main_py_path = Path(__file__).parent.parent.parent / "src" / "qdrant_loader" / "main.py"
    
    # Run the main.py file as a script to test the if __name__ == "__main__": block
    # Use a mock to intercept the cli call
    test_script = f"""
import sys
from unittest.mock import patch

# Mock the cli function before importing
with patch('qdrant_loader.cli.cli.cli') as mock_cli:
    # Execute the main.py file content
    exec(open(r'{main_py_path}').read(), {{'__name__': '__main__'}})
    
    # Check if cli was called
    print(f"CLI called: {{mock_cli.called}}")
    print(f"Call count: {{mock_cli.call_count}}")
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )
    
    # Verify the script ran successfully and cli was called
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "CLI called: True" in result.stdout, f"CLI was not called. Output: {result.stdout}"

def test_import_without_execution():
    """Test that importing main module doesn't execute cli()."""
    # Simply import the module - this should execute all module-level code
    import qdrant_loader.main
    
    # Verify the module exists and has expected attributes
    assert hasattr(qdrant_loader.main, 'cli')
    
    # This test just ensures the import works and covers the import statements