import re
import requests
from .. import config

from ..config import RANDOM_USER_AGENT

def get_embed_link(url):
    token_url = f"{config.MEGAKINO_URL}/index.php?yg=token"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    with requests.Session() as s:
        s.get(token_url, headers=headers, timeout=15)
        response = s.get(url, headers=headers, timeout=15)

    embed_match = re.search(r'iframe src="([^"]+)"', response.text)
    if embed_match:
        return embed_match.group(1)
    return None

def megakino_get_direct_link(link):
    embed_link = get_embed_link(link)
    if not embed_link:
        return None
    response = requests.get(embed_link, timeout=15, headers={
        "User-Agent": RANDOM_USER_AGENT})
    uid_match = re.search(r'"uid":"(.*?)"', response.text)
    md5_match = re.search(r'"md5":"(.*?)"', response.text)
    id_match = re.search(r'"id":"(.*?)"', response.text)

    if not all([uid_match, md5_match, id_match]):
        return None

    uid = uid_match.group(1)
    md5 = md5_match.group(1)
    video_id = id_match.group(1)

    stream_link = f"https://watch.gxplayer.xyz/m3u8/{uid}/{md5}/master.txt?s=1&id={video_id}&cache=1"
    return stream_link
