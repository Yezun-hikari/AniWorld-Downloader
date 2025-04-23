import requests
from bs4 import BeautifulSoup

from aniworld.config import DEFAULT_REQUEST_TIMEOUT, RANDOM_USER_AGENT

# Currently not working cause of capture


def get_direct_link_from_filemoon(embeded_filemoon_link: str) -> str:
    filemoon_id = embeded_filemoon_link.split('/')[-1]
    filemoon_link = f"https://filemoon.to/download/{filemoon_id}"
    response = requests.get(
        filemoon_link,
        headers={'User-Agent': RANDOM_USER_AGENT},
        timeout=DEFAULT_REQUEST_TIMEOUT
    )
    soup = BeautifulSoup(response.content, 'html.parser')

    download_link = soup.find('a', class_='button')['href']
    return download_link


if __name__ == '__main__':
    link = input("Enter Filemoon Link: ")
    print(get_direct_link_from_filemoon(embeded_filemoon_link=link))
