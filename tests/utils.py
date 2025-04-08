"""
Test utilities.
"""
import os

def is_github_actions() -> bool:
    """Check if the code is running in GitHub Actions.
    
    Returns:
        bool: True if running in GitHub Actions, False otherwise.
    """
    return os.getenv('GITHUB_ACTIONS') == 'true' 