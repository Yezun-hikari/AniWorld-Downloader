import logging
import threading
import time
from datetime import datetime, timedelta

from ..common.common import get_season_episode_count
from .download_manager import get_download_manager
from .monitored_series_manager import get_monitored_series_manager

class BackgroundChecker:
    """A class to periodically check for new episodes of monitored series."""

    def __init__(self, check_interval_hours: int = 6):
        self.monitored_series_manager = get_monitored_series_manager()
        self.download_manager = get_download_manager()
        self.check_interval = timedelta(hours=check_interval_hours)
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        """Starts the background checker thread."""
        if not self.thread.is_alive():
            self._stop_event.clear()
            self.thread.start()
            logging.info("Background episode checker started.")

    def stop(self):
        """Stops the background checker thread."""
        self._stop_event.set()
        logging.info("Background episode checker stopped.")

    def _run(self):
        """The main loop for the background checker."""
        logging.info("Background checker thread is running.")
        while not self._stop_event.is_set():
            try:
                self.check_for_new_episodes()
            except Exception as e:
                logging.error(f"An error occurred in the background checker: {e}")

            self._stop_event.wait(self.check_interval.total_seconds())

    def check_for_new_episodes(self):
        """Checks all monitored series for new episodes."""
        logging.info("Running periodic check for new episodes...")
        monitored_series = self.monitored_series_manager.get_all_series()

        for series_data in monitored_series:
            try:
                series_title = series_data["title"]
                series_url = series_data["url"]
                last_downloaded_total = series_data.get("last_episode_downloaded", 0)

                logging.info(f"Checking for new episodes of '{series_title}'...")

                slug = series_url.split("/stream/")[1].split("/")[0]

                # Determine the base URL for get_season_episode_count
                base_url_for_check = "https://s.to" if "s.to" in series_url else "https://aniworld.to"

                seasons_info = get_season_episode_count(slug, base_url_for_check)
                if not seasons_info:
                    logging.warning(f"Could not retrieve season info for '{series_title}'. Skipping.")
                    continue

                current_total_episodes = sum(seasons_info.values())

                if current_total_episodes > last_downloaded_total:
                    logging.info(f"New episodes found for '{series_title}'!")

                    all_episodes = []
                    for season, count in sorted(seasons_info.items()):
                        for episode in range(1, count + 1):
                            all_episodes.append(f"{series_url.rsplit('/', 2)[0]}/staffel-{season}/episode-{episode}")

                    new_episode_urls = all_episodes[last_downloaded_total:]

                    if new_episode_urls:
                        # For now, just download in the first language specified.
                        language = series_data["languages"][0]

                        self.download_manager.add_download(
                            anime_title=series_title,
                            episode_urls=new_episode_urls,
                            language=language,
                            provider="VOE", # Default provider for now
                            total_episodes=len(new_episode_urls)
                        )

                        # Update the count in the monitored series manager
                        self.monitored_series_manager.update_series(
                            series_title,
                            {"last_episode_downloaded": current_total_episodes, "last_check_timestamp": datetime.now().isoformat()}
                        )

            except Exception as e:
                logging.error(f"Error checking series '{series_data.get('title', 'Unknown')}': {e}")

        logging.info("Finished periodic check for new episodes.")
