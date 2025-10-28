import os
import logging
import yt_dlp
import re
import requests
from urllib.parse import urljoin
from .. import config
from ..config import DEFAULT_MOVIE_DOWNLOAD_PATH, RANDOM_USER_AGENT
from ..models import Movie
from ..action.common import sanitize_filename

def megakino_get_direct_link(url: str) -> str or None:
    """
    Robustly extracts the direct M3U8 stream link from a megakino.ms movie page.
    This combines the multi-step extraction process with proper session handling.
    """
    try:
        token_url = f"{config.MEGAKINO_URL}/index.php?yg=token"
        headers = {'User-Agent': RANDOM_USER_AGENT}

        with requests.Session() as s:
            s.get(token_url, headers=headers, timeout=15)

            main_page_response = s.get(url, headers=headers, timeout=15)
            main_page_response.raise_for_status()
            embed_match = re.search(r'iframe src="([^"]+)"', main_page_response.text)
            if not embed_match:
                logging.error(f"Could not find embed iframe src on: {url}")
                return None

            embed_link = embed_match.group(1)
            if embed_link.startswith("//"):
                embed_link = "https:" + embed_link

            player_headers = headers.copy()
            player_headers['Referer'] = url
            player_page_response = s.get(embed_link, headers=player_headers, timeout=15)
            player_page_response.raise_for_status()

            uid_match = re.search(r'"uid":"(.*?)"', player_page_response.text)
            md5_match = re.search(r'"md5":"(.*?)"', player_page_response.text)
            id_match = re.search(r'"id":"(.*?)"', player_page_response.text)

            if not all([uid_match, md5_match, id_match]):
                logging.error("Could not extract all required video metadata from player page.")
                return None

            uid, md5, video_id = uid_match.group(1), md5_match.group(1), id_match.group(1)

            stream_link = f"https://watch.gxplayer.xyz/m3u8/{uid}/{md5}/master.txt?s=1&id={video_id}&cache=1"
            logging.info(f"Successfully extracted stream link: {stream_link}")
            return stream_link

    except requests.exceptions.RequestException as e:
        logging.error(f"A network error occurred during megakino link extraction for {url}: {e}")
        return None

# A simple logger to suppress most of yt-dlp's output while capturing errors.
class QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): logging.error(f"[yt-dlp] {msg}")

def download_movie(movie: Movie, progress_callback=None) -> bool:
    """
    Downloads a movie using the yt-dlp library, combining the robust extractor
    with the correct User-Agent and Referer headers.
    """
    try:
        direct_link = megakino_get_direct_link(movie.link)
        if not direct_link:
            if progress_callback:
                progress_callback({'status': 'error', 'error': 'Could not extract direct download link.'})
            return False

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
            'http_headers': {
                'User-Agent': RANDOM_USER_AGENT,
                'Referer': movie.link,
            },
        }

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
