import re

import niquests

from ...config import DEFAULT_USER_AGENT, GLOBAL_SESSION

# Compile regex pattern once for better performance
SOURCE_LINK_PATTERN = re.compile(r'src:\s*"([^"]+)"')
IMAGE_LINK_PATTERN = re.compile(r'poster:\s*"([^"]+)"')


def get_direct_link_from_vidoza(embeded_vidoza_link):
    """Get direct Vidoza video URL."""
    try:
        resp = GLOBAL_SESSION.get(
            embeded_vidoza_link, headers={"User-Agent": DEFAULT_USER_AGENT}
        )
        resp.raise_for_status()
        html = resp.text

        if "sourcesCode:" in html:
            match = SOURCE_LINK_PATTERN.search(html)
            if match:
                return match.group(1)

    except niquests.RequestException as err:
        raise ValueError(f"Failed to fetch Vidoza page: {err}") from err


def get_preview_image_link_from_vidoza(embeded_vidoza_link):
    """Get Vidoza preview image URL."""
    try:
        resp = GLOBAL_SESSION.get(
            embeded_vidoza_link, headers={"User-Agent": DEFAULT_USER_AGENT}
        )
        resp.raise_for_status()
        html = resp.text

        if "sourcesCode:" in html:
            match = IMAGE_LINK_PATTERN.search(html)
            if match:
                return match.group(1)

    except niquests.RequestException as err:
        raise ValueError(f"Failed to fetch Vidoza page: {err}") from err
