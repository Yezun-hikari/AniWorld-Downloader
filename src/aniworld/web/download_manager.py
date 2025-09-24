"""
Download Queue Manager for AniWorld Downloader
Handles global download queue processing and status tracking
"""

import threading
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime
from .database import UserDatabase


class DownloadQueueManager:
    """Manages the global download queue processing with in-memory storage"""

    def __init__(self, database: Optional[UserDatabase] = None):
        self.db = database  # Only used for user auth, not download storage
        self.is_processing = False
        self.current_download_id = None
        self.worker_thread = None
        self._stop_event = threading.Event()

        # In-memory download queue storage
        self._next_id = 1
        self._queue_lock = threading.Lock()
        self._active_downloads = {}  # id -> download_job dict
        self._completed_downloads = []  # list of completed download jobs (keep last N)
        self._max_completed_history = 10

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
        with self._queue_lock:
            queue_id = self._next_id
            self._next_id += 1

            download_job = {
                'id': queue_id,
                'anime_title': anime_title,
                'episode_urls': episode_urls,
                'language': language,
                'provider': provider,
                'total_episodes': total_episodes,
                'completed_episodes': 0,
                'status': 'queued',
                'current_episode': '',
                'progress_percentage': 0.0,
                'error_message': '',
                'created_by': created_by,
                'created_at': datetime.now(),
                'started_at': None,
                'completed_at': None
            }

            self._active_downloads[queue_id] = download_job

        # Start processor if not running
        if not self.is_processing:
            self.start_queue_processor()

        return queue_id

    def get_queue_status(self):
        """Get current queue status"""
        with self._queue_lock:
            active_downloads = []
            for download in self._active_downloads.values():
                if download['status'] in ['queued', 'downloading']:
                    # Format for API compatibility
                    active_downloads.append({
                        'id': download['id'],
                        'anime_title': download['anime_title'],
                        'total_episodes': download['total_episodes'],
                        'completed_episodes': download['completed_episodes'],
                        'status': download['status'],
                        'current_episode': download['current_episode'],
                        'progress_percentage': download['progress_percentage'],
                        'error_message': download['error_message'],
                        'created_at': download['created_at'].isoformat() if download['created_at'] else None
                    })

            completed_downloads = []
            for download in self._completed_downloads[-1:]:  # Get last completed
                completed_downloads.append({
                    'id': download['id'],
                    'anime_title': download['anime_title'],
                    'total_episodes': download['total_episodes'],
                    'completed_episodes': download['completed_episodes'],
                    'status': download['status'],
                    'current_episode': download['current_episode'],
                    'progress_percentage': download['progress_percentage'],
                    'error_message': download['error_message'],
                    'completed_at': download['completed_at'].isoformat() if download['completed_at'] else None
                })

            return {
                'active': active_downloads,
                'completed': completed_downloads
            }

    def _process_queue(self):
        """Background worker that processes the download queue"""
        while self.is_processing and not self._stop_event.is_set():
            try:
                # Get next job
                job = self._get_next_queued_download()

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
            self._update_download_status(queue_id, 'downloading', current_episode='Starting download...')

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
                self._update_download_status(queue_id, 'failed', error_message='Failed to process episode URLs')
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

            # Update total episodes count if different from original
            if actual_total_episodes != job['total_episodes']:
                self._update_download_status(
                    queue_id,
                    'downloading',  # Keep as downloading since we're about to start
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
                    self._update_download_status(
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

            self._update_download_status(
                queue_id,
                status,
                completed_episodes=successful_downloads,
                current_episode=error_msg,
                error_message=error_msg if status == 'failed' else None
            )

        except Exception as e:
            logging.error(f"Download job {queue_id} failed: {e}")
            self._update_download_status(
                queue_id,
                'failed',
                error_message=f'Download failed: {str(e)}'
            )

    def _get_next_queued_download(self):
        """Get the next download job in the queue"""
        with self._queue_lock:
            for download in self._active_downloads.values():
                if download['status'] == 'queued':
                    return download
            return None

    def _update_download_status(self, queue_id: int, status: str, completed_episodes: int = None, current_episode: str = None, error_message: str = None, total_episodes: int = None):
        """Update the status of a download job"""
        with self._queue_lock:
            if queue_id not in self._active_downloads:
                return False

            download = self._active_downloads[queue_id]
            download['status'] = status

            if completed_episodes is not None:
                download['completed_episodes'] = completed_episodes
                # Calculate progress percentage
                total = download['total_episodes']
                download['progress_percentage'] = (completed_episodes / total * 100) if total > 0 else 0

            if current_episode is not None:
                download['current_episode'] = current_episode

            if error_message is not None:
                download['error_message'] = error_message

            if total_episodes is not None:
                download['total_episodes'] = total_episodes

            # Update timestamps based on status
            if status == 'downloading' and download['started_at'] is None:
                download['started_at'] = datetime.now()
            elif status in ['completed', 'failed']:
                download['completed_at'] = datetime.now()

                # Move to completed list and remove from active
                self._completed_downloads.append(download.copy())
                # Keep only recent completed downloads
                if len(self._completed_downloads) > self._max_completed_history:
                    self._completed_downloads = self._completed_downloads[-self._max_completed_history:]

                # Remove from active downloads
                del self._active_downloads[queue_id]

            return True


# Global instance
_download_manager = None

def get_download_manager(database: Optional[UserDatabase] = None) -> DownloadQueueManager:
    """Get or create the global download manager instance"""
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadQueueManager(database)
    return _download_manager