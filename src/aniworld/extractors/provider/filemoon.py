import re
import requests
# import jsbeautifier.unpackers.packer as packer

from aniworld import config

REDIRECT_REGEX = re.compile(
    r'<iframe *(?:[^>]+ )?src=(?:\'([^\']+)\'|"([^"]+)")[^>]*>')
SCRIPT_REGEX = re.compile(
    r'(?s)<script\s+[^>]*?data-cfasync=["\']?false["\']?[^>]*>(.+?)</script>')
VIDEO_URL_REGEX = re.compile(r'file:\s*"([^"]+\.m3u8[^"]*)"')

# TODO Implement this script fully


def get_direct_link_from_filemoon(embeded_filemoon_link: str):
    session = requests.Session()
    session.verify = False

    headers = {
        "User-Agent": config.RANDOM_USER_AGENT,
        "Referer": embeded_filemoon_link,
    }

    response = session.get(embeded_filemoon_link, headers=headers)
    source = response.text

    match = REDIRECT_REGEX.search(source)
    if match:
        redirect_url = match.group(1) or match.group(2)
        response = session.get(redirect_url, headers=headers)
        source = response.text

    for script_match in SCRIPT_REGEX.finditer(source):
        script_content = script_match.group(1).strip()

        if not script_content.startswith("eval("):
            continue

        if packer.detect(script_content):
            unpacked = packer.unpack(script_content)
            video_match = VIDEO_URL_REGEX.search(unpacked)
            if video_match:
                return video_match.group(1)

    raise Exception("No Video link found!")


if __name__ == '__main__':
    url = input("Enter Filemoon Link: ")
    print(get_direct_link_from_filemoon(url))
