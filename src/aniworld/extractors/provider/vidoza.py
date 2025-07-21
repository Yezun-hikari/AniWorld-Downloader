import re

import requests
from bs4 import BeautifulSoup

from aniworld.config import DEFAULT_REQUEST_TIMEOUT, RANDOM_USER_AGENT


# Compile regex pattern once for better performance
SOURCE_LINK_PATTERN = re.compile(r'src:\s*"([^"]+)"')


def get_direct_link_from_vidoza(embeded_vidoza_link: str) -> str:
    """
    Extract direct video link from Vidoza embed page.

    Args:
        embeded_vidoza_link: URL of the Vidoza embed page

    Returns:
        Direct video URL

    Raises:
        ValueError: If no direct link is found
        requests.RequestException: If the request fails
    """
    try:
        response = requests.get(
            embeded_vidoza_link,
            headers={'User-Agent': RANDOM_USER_AGENT},
            timeout=DEFAULT_REQUEST_TIMEOUT
        )
        response.raise_for_status()  # Raise an exception for bad status codes

        # Direct text search for better performance
        html_content = response.text
        if 'sourcesCode:' in html_content:
            match = SOURCE_LINK_PATTERN.search(html_content)
            if match:
                return match.group(1)

        # Fallback to BeautifulSoup parsing if direct search fails
        soup = BeautifulSoup(response.content, "html.parser")
        scripts = soup.find_all('script', string=True)

        for script in scripts:
            if 'sourcesCode:' in script.string:
                match = SOURCE_LINK_PATTERN.search(script.string)
                if match:
                    return match.group(1)

    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch Vidoza page: {e}") from e
    except Exception as e:
        raise ValueError(f"Error parsing Vidoza page: {e}") from e

    raise ValueError("No direct link found in Vidoza page.")


if __name__ == '__main__':
    link = input("Enter Vidoza Link: ")
    print(get_direct_link_from_vidoza(embeded_vidoza_link=link))
