import time
import logging
from git import Repo


class GitAdapter:
    def __init__(self, max_retries: int, retry_delay: int):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)

    def clone(self, url: str, local_path: str, branch: str, depth: int) -> None:
        """Clone a repository with retry logic."""
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(f"Clone attempt {attempt}/{self.max_retries}")
                self.repo = Repo.clone_from(
                    url,
                    local_path,
                    branch=branch,
                    depth=depth,
                    single_branch=True,
                    progress=self._clone_progress,
                )
                self.logger.info("Repository cloned successfully")
                return
            except Exception as e:
                self.logger.warning(f"Clone attempt {attempt} failed: {str(e)}")
                if attempt == self.max_retries:
                    self.logger.error("Failed to clone repository after maximum retries")
                    raise Exception(f"Failed to clone repository after {self.max_retries} attempts")
                time.sleep(self.retry_delay)

    def _clone_progress(self, op_code, cur_count, max_count, op_desc):
        # This method is not provided in the original file or the new code block
        # It's assumed to exist as it's called in the clone method
        pass
