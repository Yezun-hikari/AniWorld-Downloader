import os
import logging
import yt_dlp
import re
import requests
from ..config import DEFAULT_MOVIE_DOWNLOAD_PATH, RANDOM_USER_AGENT, MEGAKINO_URL
from ..models import Movie
from ..action.common import sanitize_filename
from ..extractors.provider.voe import get_direct_link_from_voe

def megakino_get_voe_link(movie_url: str) -> str or None:
    """
    Extracts the voe.sx embed link from a megakino.ms movie page.
    """
    try:
        with requests.Session() as s:
            # Handle anti-bot token
            s.get(f"{MEGAKINO_URL}/index.php?yg=token", headers={"User-Agent": RANDOM_USER_AGENT})

            # Get movie page content
            response = s.get(movie_url, headers={"User-Agent": RANDOM_USER_AGENT})
            response.raise_for_status()

            # Find the voe.sx link in the iframe's data-src attribute
            match = re.search(r'<iframe[^>]+data-src="([^"]*voe\.sx[^"]*)"', response.text)
            if match:
                voe_embed_url = match.group(1)
                logging.info(f"Found VOE embed link: {voe_embed_url}")
                return voe_embed_url
            else:
                logging.error(f"Could not find VOE embed link on page: {movie_url}")
                return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while fetching VOE link from megakino: {e}")
        return None

# A simple logger to suppress most of yt-dlp's output while capturing errors.
class QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): logging.error(f"[yt-dlp] {msg}")

def download_movie(movie: Movie, progress_callback=None) -> bool:
    """
    Downloads a movie from megakino by first extracting the voe.sx link,
    then getting the direct video URL from VOE, and finally downloading with yt-dlp.
    """
    try:
        # Step 1: Get the voe.sx embed link from the movie page.
        voe_embed_link = megakino_get_voe_link(movie.link)
        if not voe_embed_link:
            if progress_callback:
                progress_callback({'status': 'error', 'error': 'Could not find VOE video source.'})
            return False

        # Step 2: Use the existing VOE extractor to get the final, direct video link.
        direct_link = get_direct_link_from_voe(voe_embed_link)
        if not direct_link:
            if progress_callback:
                progress_callback({'status': 'error', 'error': 'Failed to extract direct link from VOE.'})
            return False

        # Step 3: Prepare download path and options.
        sanitized_title = sanitize_filename(movie.title)
        output_dir = os.path.join(DEFAULT_MOVIE_DOWNLOAD_PATH, sanitized_title)
        output_file_template = os.path.join(output_dir, f"{sanitized_title}.%(ext)s")
        os.makedirs(output_dir, exist_ok=True)

        # Standard yt-dlp options are sufficient for VOE links.
        ydl_opts = {
            'outtmpl': output_file_template,
            'nocheckcertificate': True,
            'fragment_retries': float('inf'),
            'concurrent_fragment_downloads': 4,
            'quiet': False,
            'no_warnings': True,
            'logger': QuietLogger(),
            'progress_hooks': [progress_callback] if progress_callback else [],
        }

        # Step 4: Execute the download.
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
            progress_callback({'status': 'error', 'error': 'An unexpected internal error occurred.'})
        return False
