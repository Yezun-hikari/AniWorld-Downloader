import re

import requests

from aniworld import config


def get_direct_link_from_luluvdo(embeded_luluvdo_link, arguments=None):
    luluvdo_id = embeded_luluvdo_link.split('/')[-1]
    filelink = (
        f"https://luluvdo.com/dl?op=embed&file_code={luluvdo_id}&embed=1&referer=luluvdo.com&adb=0"
    )

    # The User-Agent needs to be the same as the direct-link ones to work
    headers = {
        "Origin": "https://luluvdo.com",
        "Referer": "https://luluvdo.com/",
        "User-Agent": config.LULUVDO_USER_AGENT
    }

    if arguments:
        if arguments.action == "Download":
            headers["Accept-Language"] = "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"

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
