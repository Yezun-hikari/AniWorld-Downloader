import os
import logging
import yt_dlp
from ..extractors.megakino_extractor import megakino_get_direct_link
from ..config import DEFAULT_MOVIE_DOWNLOAD_PATH
from ..models import Movie
from ..action.common import sanitize_filename

# A simple logger to suppress most of yt-dlp's output while capturing errors.
class QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): logging.error(f"[yt-dlp] {msg}")

def download_movie(movie: Movie, progress_callback=None) -> bool:
    """
    Downloads a movie using the yt-dlp library directly.
    Returns True on success, False on failure.
    """
    try:
        # Step 1: Get the direct streamable link for the movie.
        direct_link = megakino_get_direct_link(movie.link)
        if not direct_link:
            logging.error(f"Could not get direct link for movie: {movie.title}")
            if progress_callback:
                progress_callback({'status': 'error', 'error': 'Could not extract direct download link.'})
            return False

        # Step 2: Prepare the output path and filename.
        sanitized_title = sanitize_filename(movie.title)
        output_dir = os.path.join(DEFAULT_MOVIE_DOWNLOAD_PATH, sanitized_title)

        # Use a template to let yt-dlp determine the correct extension (e.g., .mp4).
        output_file_template = os.path.join(output_dir, f"{sanitized_title}.%(ext)s")

        # Step 3: Ensure the output directory exists before starting the download.
        os.makedirs(output_dir, exist_ok=True)

        # Step 4: Configure yt-dlp options for a robust download.
        ydl_opts = {
            'outtmpl': output_file_template,
            'nocheckcertificate': True,
            'fragment_retries': 'infinite',  # Retry fragments indefinitely
            'concurrent_fragment_downloads': 4, # Speed up HLS downloads
            'quiet': False, # Must be False for progress hooks to work
            'no_warnings': True,
            'logger': QuietLogger(),
            'progress_hooks': [progress_callback] if progress_callback else [],
        }

        # Step 5: Execute the download.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([direct_link])

        return True

    except yt_dlp.utils.DownloadError as e:
        logging.error(f"A yt-dlp download error occurred for {movie.title}: {e}")
        if progress_callback:
            progress_callback({'status': 'error', 'error': str(e)})
        return False

    except Exception as e:
        logging.error(f"An unexpected error occurred while downloading {movie.title}: {e}")
        if progress_callback:
            # Provide a generic error message for unexpected issues.
            progress_callback({'status': 'error', 'error': 'An unexpected internal error occurred.'})
        return False
