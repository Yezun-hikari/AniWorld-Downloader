import re
import requests
import jsbeautifier
from bs4 import BeautifulSoup

from aniworld import config


def get_direct_link_from_filemoon(embeded_filemoon_link):
    url = embeded_filemoon_link.replace("/e/", "/d/")
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    iframe = soup.find('iframe')
    link = None
    if iframe and iframe.has_attr('src'):
        link = iframe['src']

    headers = {
        "referer": "https://filemoon.to/",
        "user-agent": config.RANDOM_USER_AGENT
    }

    response = requests.get(link, headers=headers)
    html = response.text
    unpacked = jsbeautifier.beautify(html)

    pattern = r'file:\s*"([^"]+)"'
    matches = re.findall(pattern, unpacked)
    if matches:
        return matches[0]
    raise ValueError("No match found")


if __name__ == '__main__':
    url = input("Enter Filemoon Link: ")
    print(get_direct_link_from_filemoon(url))
