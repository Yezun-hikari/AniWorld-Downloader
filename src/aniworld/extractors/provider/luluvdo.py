import re

import requests

from aniworld import config


def get_direct_link_from_luluvdo(embeded_luluvdo_link):
    luluvdo_id = embeded_luluvdo_link.split('/')[-1]
    filelink = (
        f"https://luluvdo.com/dl?op=embed&file_code={luluvdo_id}"
        "&auto=1&referer=https://aniworld.to"
    )

    # The User-Agent needs to be the same as the direct-link ones to work
    headers = {
        "User-Agent": config.LULUVDO_USER_AGENT
    }

    response = requests.get(filelink, headers=headers,
                            timeout=config.DEFAULT_REQUEST_TIMEOUT)

    if response.status_code == 200:
        pattern = r'file:\s*"([^"]+)"'
        matches = re.findall(pattern, str(response.text))

        if matches:
            return matches[0]

    raise ValueError("No match found")


if __name__ == '__main__':
    url = input("Enter Luluvdo Link: ")
    print(get_direct_link_from_luluvdo(url))
