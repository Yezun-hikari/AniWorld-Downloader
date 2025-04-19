import re
import base64
import json
import requests
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from aniworld.config import DEFAULT_REQUEST_TIMEOUT, RANDOM_USER_AGENT

REDIRECT_PATTERN = re.compile(r"https?://[^'\"<>]+")
EXTRACT_VEO_HLS_PATTERN = re.compile(r"'hls': '(?P<hls>.*)'")
HIDDEN_JSON_PATTERN = re.compile(r"var a168c='(?P<hidden_json>[^']+)'")


def get_direct_link_from_voe(embeded_voe_link: str) -> str:
    response = requests.get(
        embeded_voe_link,
        headers={'User-Agent': RANDOM_USER_AGENT},
        timeout=DEFAULT_REQUEST_TIMEOUT
    )

    redirect_match = REDIRECT_PATTERN.search(response.text)
    if not redirect_match:
        raise ValueError("No redirect link found.")

    redirect_url = redirect_match.group(0)
    try:
        with urlopen(
            Request(
                redirect_url,
                headers={'User-Agent': RANDOM_USER_AGENT}
            ),
            timeout=10
        ) as response:
            redirect_content = response.read()
        redirect_content_str = redirect_content.decode('utf-8')
    except (HTTPError, URLError, TimeoutError) as e:
        raise ValueError(f"Failed to fetch URL {redirect_url}: {e}") from e

    hidden_json_match = HIDDEN_JSON_PATTERN.search(redirect_content_str)
    if hidden_json_match:
        hidden_json = base64.b64decode(
            hidden_json_match.group("hidden_json")).decode()
        hidden_json = hidden_json[::-1]
        hidden_json = json.loads(hidden_json)
        return hidden_json["source"]

    hls_match = EXTRACT_VEO_HLS_PATTERN.search(redirect_content_str)
    if not hls_match:
        raise ValueError("No HLS link found.")

    hls_link = base64.b64decode(hls_match.group("hls")).decode()
    return hls_link


if __name__ == '__main__':
    link = input("Enter VOE Link: ")
    print(get_direct_link_from_voe(embeded_voe_link=link))
