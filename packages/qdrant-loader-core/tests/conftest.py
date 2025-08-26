import sys
from pathlib import Path

# Ensure the core src directory is importable when running tests from the monorepo root
core_src = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(core_src))
