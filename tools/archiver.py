import os
import shutil
import json
import datetime
import logging
from typing import Optional

class Archiver:
    def __init__(self, archive_root: str = "conductor/archive"):
        self.archive_root = archive_root
        os.makedirs(self.archive_root, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def archive_current_project(self, project_id: str, bundle_path: str, state_path: str, logs_path: Optional[str] = None):
        """
        Moves the project bundle, state file, and optional logs to the archive.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize project_id to be safe for filenames
        safe_id = "".join([c for c in project_id if c.isalnum() or c in ('-', '_')]).strip()
        archive_dir = os.path.join(self.archive_root, f"{timestamp}_{safe_id}")

        os.makedirs(archive_dir, exist_ok=True)

        try:
            # Move Bundle
            if bundle_path and os.path.exists(bundle_path):
                shutil.move(bundle_path, os.path.join(archive_dir, "project_bundle.json"))
                self.logger.info(f"Archived bundle to {archive_dir}")

            # Copy State (don't move, as we might want to reset it in place later, but moving is safer for history)
            # Actually, standard practice for "archive" is move. The system should reset state separately.
            if state_path and os.path.exists(state_path):
                 shutil.copy(state_path, os.path.join(archive_dir, "final_state.json"))
                 self.logger.info(f"Archived state to {archive_dir}")

            # Copy Logs if provided
            if logs_path and os.path.exists(logs_path):
                shutil.copy(logs_path, os.path.join(archive_dir, "execution.log"))

        except Exception as e:
            self.logger.error(f"Failed to archive project {project_id}: {e}")
            raise
