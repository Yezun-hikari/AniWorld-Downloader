import re
import requests
import logging
from urllib.parse import urljoin
from .. import config
from ..config import RANDOM_USER_AGENT

def megakino_get_direct_link(url: str) -> str or None:
    """
    Extracts the direct M3U8 stream link from a megakino.ms movie page.

    This function simulates the browser flow by:
    1. Initializing a session and getting an anti-bot token.
    2. Visiting the main movie page to get the embedded player URL.
    3. Visiting the embedded player page to extract video metadata.
    4. Using the metadata to get a pointer file (`master.txt`).
    5. Reading the pointer file to get the final M3U8 manifest URL.

    Args:
        url: The URL of the megakino.ms movie page.

    Returns:
        The direct M3U8 manifest link if successful, otherwise None.
    """
    try:
        token_url = f"{config.MEGAKINO_URL}/index.php?yg=token"
        headers = {'User-Agent': RANDOM_USER_AGENT}

        with requests.Session() as s:
            # Step 1: Get the anti-bot token.
            s.get(token_url, headers=headers, timeout=15)

            # Step 2: Get the main movie page and extract the iframe URL.
            main_page_response = s.get(url, headers=headers, timeout=15)
            main_page_response.raise_for_status()
            embed_match = re.search(r'iframe src="([^"]+)"', main_page_response.text)
            if not embed_match:
                logging.error(f"Could not find embed iframe src on: {url}")
                return None

            embed_link = embed_match.group(1)
            if embed_link.startswith("//"):
                embed_link = "https:" + embed_link

            # Step 3: Visit the player page to get video metadata.
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

            # Step 4: Construct the URL to the pointer file (`master.txt`).
            pointer_file_url = f"https://watch.gxplayer.xyz/m3u8/{uid}/{md5}/master.txt?s=1&id={video_id}&cache=1"

            # Step 5: Read the content of the pointer file to get the real manifest URL.
            manifest_response = s.get(pointer_file_url, headers=player_headers, timeout=15)
            manifest_response.raise_for_status()

            # The content of master.txt is the relative path to the manifest.
            manifest_path = manifest_response.text.strip()
            if not manifest_path:
                logging.error("Pointer file 'master.txt' was empty.")
                return None

            # Construct the final, absolute URL to the HLS manifest.
            final_stream_link = urljoin(pointer_file_url, manifest_path)

            logging.info(f"Successfully extracted final stream link: {final_stream_link}")
            return final_stream_link

    except requests.exceptions.RequestException as e:
        logging.error(f"A network error occurred during megakino link extraction for {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during megakino link extraction for {url}: {e}")
        return None
