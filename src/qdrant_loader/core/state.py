import json
import structlog
from pathlib import Path
from typing import Dict, List, Optional

from ..config import Settings
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)
