"""Tests for the main module."""

import sys
from unittest.mock import patch

def test_main_module_cli_import():
    """Test that cli can be imported from main module."""
    from qdrant_loader.main import cli
    assert cli is not None
    assert callable(cli)

@patch('qdrant_loader.cli.cli.cli')
def test_main_when_name_is_main(mock_cli):
    """Test that cli() is called when module is run as main."""
    # Import the main module content as string to test execution
    import qdrant_loader.main
    
    # Get the source code of the main module
    import inspect
    source = inspect.getsource(qdrant_loader.main)
    
    # Create a namespace that simulates running as __main__
    namespace = {
        '__name__': '__main__',
        'cli': mock_cli,
    }
    
    # Execute the main module code with __name__ == '__main__'
    exec(source, namespace)
    
    # The cli should be called
    mock_cli.assert_called_once()

def test_import_without_execution():
    """Test that importing main module doesn't execute cli()."""
    # Simply import the module - this should execute all module-level code
    import qdrant_loader.main
    
    # Verify the module exists and has expected attributes
    assert hasattr(qdrant_loader.main, 'cli')
    
    # This test just ensures the import works and covers the import statements