import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .. import config

class MonitoredSeriesManager:
    """Manages the list of monitored series for auto-downloading."""

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path:
            self.storage_path = storage_path
        else:
            self.storage_path = config.APP_DATA_PATH / "monitored_series.json"

        self._monitored_series: Dict[str, Dict] = {}
        self._load_monitored_series()

    def _load_monitored_series(self):
        """Load the monitored series from the JSON file."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._monitored_series = json.load(f)
                logging.info(f"Loaded {len(self._monitored_series)} monitored series from {self.storage_path}")
            else:
                logging.info("No monitored series file found. Starting with an empty list.")
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Failed to load monitored series file: {e}")

    def _save_monitored_series(self):
        """Save the current list of monitored series to the JSON file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._monitored_series, f, indent=4)
        except IOError as e:
            logging.error(f"Failed to save monitored series file: {e}")

    def add_series(self, series_title: str, language: str, series_url: str):
        """Add a new series to the monitoring list or update an existing one."""
        if series_title in self._monitored_series:
            logging.info(f"Series '{series_title}' is already monitored. Updating languages.")
            if language not in self._monitored_series[series_title]["languages"]:
                self._monitored_series[series_title]["languages"].append(language)
        else:
            logging.info(f"Adding new series to monitor: '{series_title}'")
            self._monitored_series[series_title] = {
                "title": series_title,
                "url": series_url,
                "languages": [language],
                "last_episode_downloaded": 0,
                "last_check_timestamp": None,
                "added_at": datetime.now().isoformat(),
            }

        self._save_monitored_series()

    def remove_series(self, series_title: str):
        """Remove a series from the monitoring list."""
        if series_title in self._monitored_series:
            logging.info(f"Removing '{series_title}' from monitored list.")
            del self._monitored_series[series_title]
            self._save_monitored_series()
            return True
        return False

    def get_all_series(self) -> List[Dict]:
        """Return a list of all monitored series."""
        return list(self._monitored_series.values())

    def get_series(self, series_title: str) -> Optional[Dict]:
        """Get a specific monitored series by its title."""
        return self._monitored_series.get(series_title)

    def update_series(self, series_title: str, updates: Dict):
        """Update a monitored series with new data."""
        if series_title in self._monitored_series:
            self._monitored_series[series_title].update(updates)
            self._save_monitored_series()
            logging.info(f"Updated monitored series '{series_title}'.")
            return True
        return False

# Global instance
_monitored_series_manager = None

def get_monitored_series_manager() -> MonitoredSeriesManager:
    """Get or create the global monitored series manager instance."""
    global _monitored_series_manager
    if _monitored_series_manager is None:
        _monitored_series_manager = MonitoredSeriesManager()
    return _monitored_series_manager
