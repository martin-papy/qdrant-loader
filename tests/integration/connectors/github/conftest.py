"""
Shared fixtures for Git connector tests.
"""
import os
from pathlib import Path
import pytest
from dotenv import load_dotenv
from qdrant_loader.config import Settings, initialize_config, get_settings

# Load test environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env.test")

@pytest.fixture(scope="session")
def is_github_actions():
    """Check if running in GitHub Actions environment."""
    return os.getenv('GITHUB_ACTIONS') == 'true'

@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from environment variables and config file."""
    # Load settings from YAML
    config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
    initialize_config(config_path)
    return get_settings()

@pytest.fixture(autouse=True)
def disable_git_prompt():
    """Disable Git credential prompts for all tests."""
    original_prompt = os.environ.get('GIT_TERMINAL_PROMPT')
    original_askpass = os.environ.get('GIT_ASKPASS')
    
    # Disable both credential prompts and credential helpers
    os.environ['GIT_TERMINAL_PROMPT'] = '0'
    os.environ['GIT_ASKPASS'] = 'echo'
    
    yield
    
    # Restore original values
    if original_prompt is not None:
        os.environ['GIT_TERMINAL_PROMPT'] = original_prompt
    else:
        del os.environ['GIT_TERMINAL_PROMPT']
        
    if original_askpass is not None:
        os.environ['GIT_ASKPASS'] = original_askpass
    else:
        del os.environ['GIT_ASKPASS'] 