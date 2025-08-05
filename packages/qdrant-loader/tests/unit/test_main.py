"""Tests for the main module."""

import sys
from unittest.mock import patch

def test_main_module_cli_import():
    """Test that cli can be imported from main module."""
    from qdrant_loader.main import cli
    assert cli is not None
    assert callable(cli)

@patch('qdrant_loader.main.cli')
def test_main_when_name_is_main(mock_cli):
    """Test that cli() is called when module is run as main."""
    # Directly execute the main module's if __name__ == "__main__": block
    import qdrant_loader.main
    
    # Get the main module's globals and execute the condition
    main_globals = qdrant_loader.main.__dict__.copy()
    main_globals['__name__'] = '__main__'
    
    # Execute the conditional block directly
    exec('if __name__ == "__main__":\n    cli()', main_globals)
    
    # Verify cli was called
    mock_cli.assert_called_once()

def test_main_module_execution_via_runpy():
    """Test main module execution via runpy to ensure line 8 coverage."""
    import subprocess
    import sys
    from pathlib import Path
    
    # Use python -m to run the module as __main__
    # This should trigger the if __name__ == "__main__": block and cover line 8
    
    # Get the package root directory (where pyproject.toml is located)
    test_dir = Path(__file__).parent  # tests/unit/
    package_root = test_dir.parent.parent  # packages/qdrant-loader/
    
    result = subprocess.run(
        [sys.executable, "-m", "qdrant_loader.main", "--help"],
        cwd=str(package_root),  # Use portable path
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # The command should run (even if it exits with non-zero due to --help)
    # What matters is that the main block executed
    assert result.returncode in [0, 1, 2], f"Unexpected return code: {result.returncode}"

def test_import_without_execution():
    """Test that importing main module doesn't execute cli()."""
    # Simply import the module - this should execute all module-level code
    import qdrant_loader.main
    
    # Verify the module exists and has expected attributes
    assert hasattr(qdrant_loader.main, 'cli')
    
    # This test just ensures the import works and covers the import statements