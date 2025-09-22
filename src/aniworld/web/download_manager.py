"""
Download Queue Manager for AniWorld Downloader
Handles global download queue processing and status tracking
"""

import threading
import time
import logging
from typing import Optional
from .database import UserDatabase


class DownloadQueueManager:
    """Manages the global download queue processing"""

    def __init__(self, database: UserDatabase):
        self.db = database
        self.is_processing = False
        self.current_download_id = None
        self.worker_thread = None
        self._stop_event = threading.Event()

    def start_queue_processor(self):
        """Start the background queue processor"""
        if not self.is_processing:
            self.is_processing = True
            self._stop_event.clear()
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logging.info("Download queue processor started")

    def stop_queue_processor(self):
        """Stop the background queue processor"""
        if self.is_processing:
            self.is_processing = False
            self._stop_event.set()
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            logging.info("Download queue processor stopped")

    def add_download(self, anime_title: str, episode_urls: list, language: str, provider: str, total_episodes: int, created_by: int = None) -> int:
        """Add a download to the queue"""
        queue_id = self.db.add_to_download_queue(anime_title, episode_urls, language, provider, total_episodes, created_by)

        # Start processor if not running
        if not self.is_processing:
            self.start_queue_processor()

        return queue_id

    def get_queue_status(self):
        """Get current queue status"""
        return self.db.get_download_queue_status()

    def _process_queue(self):
        """Background worker that processes the download queue"""
        while self.is_processing and not self._stop_event.is_set():
            try:
                # Get next job
                job = self.db.get_next_queued_download()

                if job:
                    self.current_download_id = job['id']
                    self._process_download_job(job)
                    self.current_download_id = None
                else:
                    # No jobs, wait a bit
                    time.sleep(2)

            except Exception as e:
                logging.error(f"Error in queue processor: {e}")
                time.sleep(5)

    def _process_download_job(self, job):
        """Process a single download job"""
        queue_id = job['id']

        try:
            # Mark as downloading
            self.db.update_download_status(queue_id, 'downloading', current_episode='Starting download...')

            # Import necessary modules
            from ..entry import _group_episodes_by_series
            from ..execute import _execute_single_anime
            from ..models import Anime
            from pathlib import Path
            from ..action.common import sanitize_filename
            from .. import config
            import os

            # Process episodes
            anime_list = _group_episodes_by_series(job['episode_urls'])

            if not anime_list:
                self.db.update_download_status(queue_id, 'failed', error_message='Failed to process episode URLs')
                return

            # Apply settings to anime objects
            for anime in anime_list:
                anime.language = job['language']
                anime.provider = job['provider']
                anime.action = "Download"
                for episode in anime.episode_list:
                    episode._selected_language = job['language']
                    episode._selected_provider = job['provider']

            # Calculate actual total episodes after processing URLs
            actual_total_episodes = sum(len(anime.episode_list) for anime in anime_list)

            # Update total episodes count in database if different from original
            if actual_total_episodes != job['total_episodes']:
                self.db.update_download_status(
                    queue_id,
                    'queued',
                    total_episodes=actual_total_episodes,
                    current_episode=f'Found {actual_total_episodes} valid episode(s) to download'
                )

            # Download logic
            successful_downloads = 0
            failed_downloads = 0
            current_episode_index = 0

            # Get download directory from arguments (which includes -o parameter)
            from ..parser import arguments
            download_dir = str(getattr(config, 'DEFAULT_DOWNLOAD_PATH', os.path.expanduser('~/Downloads')))
            if hasattr(arguments, 'output_dir') and arguments.output_dir is not None:
                download_dir = str(arguments.output_dir)

            for anime in anime_list:
                for episode in anime.episode_list:
                    if self._stop_event.is_set():
                        break

                    episode_info = f"{anime.title} - Episode {episode.episode} (Season {episode.season})"

                    # Update progress
                    self.db.update_download_status(
                        queue_id,
                        'downloading',
                        completed_episodes=current_episode_index,
                        current_episode=f"Downloading {episode_info}"
                    )

                    try:
                        # Create temp anime with single episode
                        temp_anime = Anime(
                            title=anime.title,
                            slug=anime.slug,
                            site=anime.site,
                            language=anime.language,
                            provider=anime.provider,
                            action=anime.action,
                            episode_list=[episode]
                        )

                        # Execute download and capture result
                        try:
                            # Check files before download to better detect success
                            import glob
                            from pathlib import Path

                            # Use the actual configured download directory
                            anime_download_dir = Path(download_dir) / sanitize_filename(anime.title)

                            # Count files before download
                            files_before = 0
                            if anime_download_dir.exists():
                                files_before = len(list(anime_download_dir.glob('*')))

                            _execute_single_anime(temp_anime)

                            # Count files after download
                            files_after = 0
                            if anime_download_dir.exists():
                                files_after = len(list(anime_download_dir.glob('*')))

                            # Check if any new files were created
                            if files_after > files_before:
                                successful_downloads += 1
                                logging.info(f"Downloaded: {episode_info}")
                            else:
                                failed_downloads += 1
                                logging.warning(f"Failed to download: {episode_info} - No new files created")

                        except Exception as download_error:
                            # If an exception was raised during download, it failed
                            failed_downloads += 1
                            logging.warning(f"Failed to download: {episode_info} - Error: {download_error}")

                    except Exception as e:
                        failed_downloads += 1
                        logging.error(f"Error downloading {episode_info}: {e}")

                    current_episode_index += 1

            # Final status update
            total_attempted = successful_downloads + failed_downloads
            if successful_downloads == 0 and failed_downloads > 0:
                status = 'failed'
                error_msg = f'Download failed: No episodes downloaded out of {failed_downloads} attempted.'
            elif failed_downloads > 0:
                status = 'completed'  # Partial success still counts as completed
                error_msg = f'Partially completed: {successful_downloads}/{total_attempted} episodes downloaded.'
            else:
                status = 'completed'
                error_msg = f'Successfully downloaded {successful_downloads} episode(s).'

            self.db.update_download_status(
                queue_id,
                status,
                completed_episodes=successful_downloads,
                current_episode=error_msg,
                error_message=error_msg if status == 'failed' else None
            )

        except Exception as e:
            logging.error(f"Download job {queue_id} failed: {e}")
            self.db.update_download_status(
                queue_id,
                'failed',
                error_message=f'Download failed: {str(e)}'
            )


# Global instance
_download_manager = None

def get_download_manager(database: UserDatabase = None) -> DownloadQueueManager:
    """Get or create the global download manager instance"""
    global _download_manager
    if _download_manager is None and database:
        _download_manager = DownloadQueueManager(database)
    return _download_manager