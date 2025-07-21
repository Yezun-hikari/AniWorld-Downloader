import re
import logging
from typing import Optional

import requests
import jsbeautifier
from bs4 import BeautifulSoup

from aniworld.config import RANDOM_USER_AGENT, DEFAULT_REQUEST_TIMEOUT

# Constants
FILEMOON_BASE_URL = "https://filemoon.to/"
FILE_PATTERN = r'file:\s*"([^"]+)"'


def _get_headers() -> dict:
    """Get request headers for Filemoon."""
    return {"referer": FILEMOON_BASE_URL, "user-agent": RANDOM_USER_AGENT}


def _make_request(url: str, headers: Optional[dict] = None) -> requests.Response:
    """Make HTTP request with error handling."""
    try:
        response = requests.get(url, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        raise


def _convert_embed_to_download_url(embed_url: str) -> str:
    """Convert embed URL to download URL format."""
    if "/e/" not in embed_url:
        logging.warning(f"URL doesn't contain '/e/' pattern: {embed_url}")
        return embed_url

    download_url = embed_url.replace("/e/", "/d/")
    logging.debug(f"Converted embed URL: {embed_url} -> {download_url}")
    return download_url


def _extract_iframe_src(html_content: str, source_url: str) -> str:
    """Extract iframe src from HTML content."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        iframe = soup.find("iframe")

        if not iframe or not iframe.has_attr("src"):
            raise ValueError(f"No iframe with src attribute found in {source_url}")

        iframe_src = iframe["src"]
        logging.debug(f"Extracted iframe src: {iframe_src}")
        return iframe_src

    except Exception as e:
        logging.error(f"Failed to extract iframe from {source_url}: {e}")
        raise


def _beautify_javascript(html_content: str) -> str:
    """Beautify JavaScript content for easier parsing."""
    try:
        beautified = jsbeautifier.beautify(html_content)
        logging.debug("Successfully beautified JavaScript content")
        return beautified
    except Exception as e:
        logging.error(f"Failed to beautify JavaScript: {e}")
        # Return original content if beautification fails
        return html_content


def _extract_file_url(content: str, source_url: str) -> str:
    """Extract file URL from beautified content."""
    matches = re.findall(FILE_PATTERN, content)

    if not matches:
        logging.error(f"No file URL found in content from {source_url}")
        raise ValueError(f"No file URL found in {source_url}")

    # Take the first match
    file_url = matches[0]
    logging.debug(f"Extracted file URL: {file_url}")
    return file_url


def get_direct_link_from_filemoon(embeded_filemoon_link: str) -> str:
    """
    Extract direct download link from Filemoon embed URL.

    Args:
        embeded_filemoon_link: Filemoon embed URL

    Returns:
        Direct download link

    Raises:
        ValueError: If required data cannot be extracted
        requests.RequestException: If HTTP requests fail
    """
    if not embeded_filemoon_link:
        raise ValueError("Embed URL cannot be empty")

    logging.info(f"Extracting direct link from Filemoon: {embeded_filemoon_link}")

    try:
        # Convert embed URL to download URL
        download_url = _convert_embed_to_download_url(embeded_filemoon_link)

        # Get initial page content
        logging.debug("Fetching download page content...")
        response = _make_request(download_url)

        # Extract iframe src
        iframe_src = _extract_iframe_src(response.text, download_url)

        # Get iframe content with proper headers
        logging.debug("Fetching iframe content...")
        headers = _get_headers()
        iframe_response = _make_request(iframe_src, headers)

        # Beautify JavaScript content
        beautified_content = _beautify_javascript(iframe_response.text)

        # Extract file URL
        file_url = _extract_file_url(beautified_content, iframe_src)

        logging.info("Successfully extracted Filemoon direct link")
        return file_url

    except Exception as e:
        logging.error(f"Failed to extract direct link from Filemoon: {e}")
        raise


if __name__ == "__main__":
    # Setup basic logging for standalone execution
    logging.basicConfig(level=logging.DEBUG)

    try:
        url = input("Enter Filemoon Link: ").strip()
        if not url:
            print("Error: No URL provided")
            exit(1)

        result = get_direct_link_from_filemoon(url)
        print(f"Direct Link: {result}")

    except Exception as e:
        print(f"Error: {e}")
        exit(1)
