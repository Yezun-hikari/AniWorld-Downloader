import os
import logging
import yt_dlp
import re
import requests
from ..config import DEFAULT_MOVIE_DOWNLOAD_PATH, RANDOM_USER_AGENT, MEGAKINO_URL
from ..models import Movie
from ..action.common import sanitize_filename
from ..extractors.provider.voe import get_direct_link_from_voe
from ..extractors.provider.gxplayer import get_direct_link_from_gxplayer

def get_movie_providers(movie_url: str) -> list:
    """
    Extracts all available video provider embed links from a megakino movie page.
    """
    providers = []
    try:
        with requests.Session() as s:
            # Handle anti-bot token
            s.get(f"{MEGAKINO_URL}/index.php?yg=token", headers={"User-Agent": RANDOM_USER_AGENT})

            # Get movie page content
            response = s.get(movie_url, headers={"User-Agent": RANDOM_USER_AGENT})
            response.raise_for_status()

            # Find all iframe embed links
            iframe_urls = re.findall(r'<iframe[^>]+data-src="([^"]*)"', response.text)

            for url in iframe_urls:
                if 'voe.sx' in url:
                    providers.append({'name': 'VOE', 'url': url})
                    logging.info(f"Found VOE embed link: {url}")
                elif 'gxplayer' in url:
                    # Placeholder for GxPlayer
                    providers.append({'name': 'GxPlayer', 'url': url})
                    logging.info(f"Found GxPlayer embed link: {url}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while fetching providers from megakino: {e}")

    return providers


# A simple logger to suppress most of yt-dlp's output while capturing errors.
class QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): logging.error(f"[yt-dlp] {msg}")

def download_movie(movie: Movie, provider: dict, progress_callback=None) -> bool:
    """
    Downloads a movie from a selected provider by extracting the direct video URL
    and then downloading with yt-dlp.
    """
    try:
        provider_name = provider.get("name")
        provider_url = provider.get("url")
        direct_link = None

        logging.info(f"Attempting to download '{movie.title}' from provider: {provider_name}")

        # Step 1: Get the direct video link from the selected provider.
        if provider_name == "VOE":
            direct_link = get_direct_link_from_voe(provider_url)
        elif provider_name == "GxPlayer":
            direct_link = get_direct_link_from_gxplayer(provider_url)
        else:
            logging.error(f"Unsupported provider: {provider_name}")
            if progress_callback:
                progress_callback({'status': 'error', 'error': f'Unsupported provider: {provider_name}'})
            return False

        if not direct_link:
            if progress_callback:
                progress_callback({'status': 'error', 'error': f'Failed to extract direct link from {provider_name}.'})
            return False

        # Step 2: Prepare download path and options.
        sanitized_title = sanitize_filename(movie.title)
        output_dir = os.path.join(DEFAULT_MOVIE_DOWNLOAD_PATH, sanitized_title)
        output_file_template = os.path.join(output_dir, f"{sanitized_title}.%(ext)s")
        os.makedirs(output_dir, exist_ok=True)

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

        # Step 3: Execute the download.
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
