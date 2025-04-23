import re
import json
import sys
import requests
from aniworld.config import DEFAULT_REQUEST_TIMEOUT


def fetch_page_content(url):
    try:
        response = requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch the page content: {e}")
        return None


def extract_video_data(page_content):
    match = re.search(r'^.*videos_manifest.*$', page_content, re.MULTILINE)
    if not match:
        raise ValueError("Failed to extract video manifest from the response.")

    json_str = match.group(0)[match.group(0).find(
        '{'):match.group(0).rfind('}') + 1]
    return json.loads(json_str)


def get_streams(url):
    page_content = fetch_page_content(url)
    data = extract_video_data(page_content)
    video_info = data['state']['data']['video']
    name = video_info['hentai_video']['name']
    streams = video_info['videos_manifest']['servers'][0]['streams']

    return {"name": name, "streams": streams}


def display_streams(streams):
    if not streams:
        print("No streams available.")
        return

    print("Available qualities:")
    for i, stream in enumerate(streams, 1):
        premium_tag = "(Premium)" if not stream['is_guest_allowed'] else ""
        print(
            f"{i}. {stream['width']}x{stream['height']}\t"
            f"({stream['filesize_mbs']}MB) {premium_tag}")


def get_user_selection(streams):
    try:
        selected_index = int(input("Select a stream: ").strip()) - 1
        if 0 <= selected_index < len(streams):
            return selected_index

        print("Invalid selection.")
        return None
    except ValueError:
        print("Invalid input.")
        return None


def get_direct_link_from_hanime(url=None):
    try:
        if url is None:
            if len(sys.argv) > 1:
                url = sys.argv[1]
            else:
                url = input("Please enter the hanime.tv video URL: ").strip()

        try:
            video_data = get_streams(url)
            print(f"Video: {video_data['name']}")
            print('*' * 40)
            display_streams(video_data['streams'])

            selected_index = None
            while selected_index is None:
                selected_index = get_user_selection(video_data['streams'])

            print(f"M3U8 URL: {video_data['streams'][selected_index]['url']}")
        except ValueError as e:
            print(f"Error: {e}")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    get_direct_link_from_hanime()
