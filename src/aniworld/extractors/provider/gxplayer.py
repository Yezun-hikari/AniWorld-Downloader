import re
import requests
from ....config import RANDOM_USER_AGENT

def get_direct_link_from_gxplayer(embed_url: str) -> str or None:
    """
    Extracts the direct m3u8 stream link from a gxplayer.xyz embed URL.
    """
    try:
        response = requests.get(embed_url, timeout=15, headers={"User-Agent": RANDOM_USER_AGENT})
        response.raise_for_status()

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

    except requests.RequestException as e:
        print(f"Error: Unable to fetch the gxplayer page. Details: {e}")
        return None
