import requests
import json
from urllib.parse import urlparse


def get_direct_link_from_loadx(embeded_loadx_link: str):
    response = requests.head(
        embeded_loadx_link, allow_redirects=True, verify=False)

    parsed_url = urlparse(response.url)
    path_parts = parsed_url.path.split("/")
    if len(path_parts) < 3:
        raise ValueError("Invalid path!")

    id_hash = path_parts[2]
    host = parsed_url.netloc

    post_url = f"https://{host}/player/index.php?data={id_hash}&do=getVideo"
    headers = {"X-Requested-With": "XMLHttpRequest"}
    response = requests.post(post_url, headers=headers, verify=False)

    data = json.loads(response.text)
    video_url = data.get("videoSource")
    if not video_url:
        raise ValueError("No Video link found!")

    return video_url


if __name__ == '__main__':
    url = input("Enter Loadx Link: ")
    print(get_direct_link_from_loadx(url))
