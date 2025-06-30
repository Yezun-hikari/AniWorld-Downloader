import json
import logging
import platform
import shutil
import subprocess
import sys
import os
import re

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

from aniworld.config import (
    DEFAULT_REQUEST_TIMEOUT,
    MPV_DIRECTORY,
    ANIWORLD_TO,
    MPV_SCRIPTS_DIRECTORY,
    DEFAULT_APPDATA_PATH,
    MPV_PATH,
    SYNCPLAY_PATH
)


def check_avx2_support() -> bool:
    if platform.system() != "Windows":
        logging.debug("AVX2 check is only supported on Windows.")
        return False

    import cpuinfo  # type: ignore # pylint: disable=import-outside-toplevel

    info = cpuinfo.get_cpu_info()
    flags = info.get('flags', [])

    if 'avx2' in flags:
        return True

    return False


def get_github_release(repo: str) -> dict:
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        response = requests.get(api_url, timeout=DEFAULT_REQUEST_TIMEOUT)
        response.raise_for_status()
        release_data = response.json()
        assets = release_data.get('assets', [])
        return {asset['name']: asset['browser_download_url'] for asset in assets}
    except (json.JSONDecodeError, requests.RequestException) as e:
        logging.error("Failed to fetch release data from GitHub: %s", e)
    return {}


# This is necessary to keep due to the error that occurs when using py7zr.
# Error: (b'\x03\x03\x01\x1b', 'BCJ2 filter is not supported by py7zr.
# Please consider to contribute to XZ/liblzma project and help Python core team implementing it.
# Or please use another tool to extract it.')

def download_7z(zip_tool: str) -> None:
    if not os.path.exists(zip_tool):
        print("Downloading 7z...")
        download_file('https://7-zip.org/a/7zr.exe', zip_tool)


def download_mpv(dep_path: str = None, appdata_path: str = None, update: bool = False):  # pylint: disable=too-many-branches, too-many-locals, too-many-branches
    if update:
        print("Updating MPV...")

    if sys.platform == 'darwin':
        if shutil.which("brew"):
            if update:
                print("Updating MPV using Homebrew...")
                subprocess.run(["brew", "update"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["brew", "upgrade", "--formula", "mpv"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            if not shutil.which("mpv"):
                print("Installing MPV using Homebrew...")
                subprocess.run(["brew", "update"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["brew", "install", "--formula", "mpv"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        return

    if sys.platform == 'linux':
        if not MPV_PATH:
            print("Automatically downloading mpv is not implemented yet on Linux.\n"
                  "You need to install it yourself with your Package-Manager!")
        return

    if sys.platform != 'win32':
        return

    appdata_path = appdata_path or DEFAULT_APPDATA_PATH
    dep_path = dep_path or os.path.join(appdata_path, "mpv")
    if update is True:
        if os.path.exists(dep_path):
            shutil.rmtree(dep_path)
    os.makedirs(dep_path, exist_ok=True)

    executable_path = os.path.join(dep_path, 'mpv.exe')
    zip_path = os.path.join(dep_path, 'mpv.7z')
    zip_tool = os.path.join(appdata_path, "7z", "7zr.exe")
    os.makedirs(os.path.dirname(zip_tool), exist_ok=True)

    if os.path.exists(executable_path):
        return

    direct_links = get_github_release("shinchiro/mpv-winbuild-cmake")
    avx2_supported = check_avx2_support()
    pattern = (
        r'mpv-x86_64-v3-\d{8}-git-[a-f0-9]{7}\.7z'
        if avx2_supported
        else r'mpv-x86_64-\d{8}-git-[a-f0-9]{7}\.7z'
    )
    logging.debug("Downloading MPV using pattern: %s", pattern)
    direct_link = next(
        (link for name, link in direct_links.items() if re.match(pattern, name)),
        None
    )

    if not direct_link:
        logging.error(
            "No suitable MPV download link found. Please download manually.")
        return

    if not os.path.exists(zip_path):
        logging.debug("Downloading MPV from %s to %s", direct_link, zip_path)
        print(
            f"Downloading MPV ({'without' if not avx2_supported else 'with'} AVX2)...")
        download_file(direct_link, zip_path)

    download_7z(zip_tool)

    logging.debug("Extracting MPV to %s", dep_path)
    try:
        subprocess.run(
            [zip_tool, "x", zip_path],
            check=True,
            cwd=dep_path,
            stdout=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError,
            subprocess.SubprocessError) as e:
        logging.error("Failed to extract files: %s", e)

    logging.debug("Adding MPV path to environment: %s", dep_path)
    os.environ["PATH"] += os.pathsep + dep_path

    if os.path.exists(zip_path):
        os.remove(zip_path)


def download_syncplay(dep_path: str = None, appdata_path: str = None, update: bool = False):
    if update:
        print("Updating Syncplay...")

    if sys.platform == 'darwin':
        if shutil.which("brew"):
            if update:
                print("Updating Syncplay using Homebrew...")
                subprocess.run(["brew", "update"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["brew", "upgrade", "--formula", "syncplay"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            if not shutil.which("syncplay"):
                print("Installing Syncplay using Homebrew...")
                subprocess.run(["brew", "update"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["brew", "install", "--formula", "syncplay"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        return

    if sys.platform == 'linux':
        if not SYNCPLAY_PATH:
            print("Automatically downloading mpv is not implemented yet on Linux.\n"
                  "You need to install it yourself with your Package-Manager!")
        return

    if sys.platform != 'win32':
        return

    appdata_path = appdata_path or DEFAULT_APPDATA_PATH
    dep_path = dep_path or os.path.join(appdata_path, "syncplay")
    if update is True:
        if os.path.exists(dep_path):
            shutil.rmtree(dep_path)
    os.makedirs(dep_path, exist_ok=True)

    executable_path = os.path.join(dep_path, 'SyncplayConsole.exe')
    zip_path = os.path.join(dep_path, 'syncplay.zip')

    if os.path.exists(executable_path):
        return

    direct_links = get_github_release("Syncplay/syncplay")
    direct_link = next(
        (link for name, link in direct_links.items()
         if re.match(r'Syncplay_\d+\.\d+\.\d+_Portable\.zip', name)),
        None
    )

    if not os.path.exists(executable_path):
        print("Downloading Syncplay...")
        download_file(direct_link, zip_path)

    logging.debug("Extracting Syncplay to %s", dep_path)
    try:
        subprocess.run(
            ["tar", "-xf", zip_path],
            check=True,
            cwd=dep_path
        )
    except subprocess.CalledProcessError as e:
        logging.error("Failed to extract files: %s", e)
    except FileNotFoundError:
        logging.error("7zr.exe not found at the specified path.")
    except subprocess.SubprocessError as e:
        logging.error("An error occurred: %s", e)

    if os.path.exists(zip_path):
        os.remove(zip_path)


def download_file(url: str, path: str):
    try:
        response = requests.get(
            url, stream=True, allow_redirects=True, timeout=DEFAULT_REQUEST_TIMEOUT)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        t = tqdm(total=total_size, unit='B', unit_scale=True)
        with open(path, 'wb') as f:
            for data in response.iter_content(block_size):
                t.update(len(data))
                f.write(data)
        t.close()
    except requests.RequestException as e:
        logging.error("Failed to download: %s", e)


def get_season_episode_count(slug) -> dict:
    base_url = f"{ANIWORLD_TO}/anime/stream/{slug}/"
    response = requests.get(base_url, timeout=DEFAULT_REQUEST_TIMEOUT)
    soup = BeautifulSoup(response.content, 'html.parser')

    season_meta = soup.find('meta', itemprop='numberOfSeasons')
    number_of_seasons = int(season_meta['content']) if season_meta else 0

    episode_counts = {}

    for season in range(1, number_of_seasons + 1):
        season_url = f"{base_url}staffel-{season}"
        response = requests.get(season_url, timeout=DEFAULT_REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.content, 'html.parser')

        episode_links = soup.find_all('a', href=True)
        unique_links = set(
            link['href']
            for link in episode_links
            if f"staffel-{season}/episode-" in link['href']
        )

        episode_counts[season] = len(unique_links)

    return episode_counts


def get_movie_episode_count(slug) -> int:
    movie_page_url = f"{ANIWORLD_TO}/anime/stream/{slug}/filme"
    response = requests.get(
        movie_page_url, timeout=DEFAULT_REQUEST_TIMEOUT)

    parsed_html = BeautifulSoup(response.content, 'html.parser')
    movie_indices = []

    movie_index = 1
    while True:
        expected_subpath = f"{slug}/filme/film-{movie_index}"

        matching_links = [link['href'] for link in parsed_html.find_all(
            'a', href=True) if expected_subpath in link['href']]

        if matching_links:
            movie_indices.append(movie_index)
            movie_index += 1
        else:
            break

    # has_movies = bool(movie_indices)
    return max(movie_indices) if movie_indices else 0


def generate_links(urls, arguments):  # pylint: disable=too-many-locals, too-many-branches
    """
    Example usage:
    seasons = {1: 12, 2: 13, 3: 4}
    base_url = [
        "https://aniworld.to/anime/stream/food-wars-shokugeki-no-sma/staffel-1/episode-1",
        "https://aniworld.to/anime/stream/food-wars-shokugeki-no-sma/staffel-2",
        "https://aniworld.to/anime/stream/overlord"
    ]
    result = generate_links(base_url)

    for url in result:
        print(url)
    """

    unique_links = set()

    slug_cache = {}
    for base_url in urls:
        parts = base_url.split('/')

        if ("anime" in parts and not "episode" in base_url and not "film-" in base_url
                or "anime" in parts and arguments.keep_watching):
            series_slug_index = parts.index("stream") + 1
            series_slug = parts[series_slug_index]

            if series_slug in slug_cache:
                seasons_info, movies_info = slug_cache[series_slug]
            else:
                seasons_info = get_season_episode_count(slug=series_slug)
                movies_info = get_movie_episode_count(slug=series_slug)
                slug_cache[series_slug] = (seasons_info, movies_info)
        else:
            unique_links.add(base_url)
            continue

        # print(seasons_info)

        if base_url.endswith("/"):
            base_url = base_url[:-1]

        parts = base_url.split("/")

        if arguments.keep_watching:
            season_start = 1
            episode_start = 1
            movie_start = 1
            season_match = re.search(r"staffel-(\d+)", base_url)
            episode_match = re.search(r"episode-(\d+)", base_url)
            movie_match = re.search(r"film-(\d+)", base_url)

            if season_match:
                season_start = int(season_match.group(1))

            if episode_match:
                episode_start = int(episode_match.group(1))

            if movie_match:
                movie_start = int(movie_match.group(1))

            raw_url = "/".join(base_url.split("/")[:6])

            if "film" not in base_url:
                for season in range(season_start, len(seasons_info) + 1):
                    season_url = f"{raw_url}/staffel-{season}/"
                    for episode in range(episode_start, seasons_info[season] + 1):
                        unique_links.add(f"{season_url}episode-{episode}")
                    episode_start = 1
                continue

            for episode in range(movie_start, movies_info + 1):
                unique_links.add(f"{raw_url}/filme/film-{episode}")
            continue

        if "staffel" not in base_url and "episode" not in base_url and not "film" in base_url:
            for season, episodes in seasons_info.items():
                season_url = f"{base_url}/staffel-{season}/"
                for episode in range(1, episodes + 1):
                    unique_links.add(f"{season_url}episode-{episode}")
            continue

        if "staffel" in base_url and "episode" not in base_url:
            season = int(parts[-1].split("-")[-1])
            if season in seasons_info:
                for episode in range(1, seasons_info[season] + 1):
                    unique_links.add(f"{base_url}/episode-{episode}")
            continue

        if "filme" in base_url and "film-" not in base_url:
            for episode in range(1, movies_info + 1):
                unique_links.add(f"{base_url}/film-{episode}")
            continue

        unique_links.add(base_url)

    def natural_sort_key(link_url):
        return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', link_url)]

    return sorted(unique_links, key=natural_sort_key)


def remove_anime4k():
    anime4k_shader_path = os.path.join(MPV_DIRECTORY, "shaders")
    anime4k_input_conf_path = os.path.join(MPV_DIRECTORY, "input.conf")
    anime4k_mpv_conf_path = os.path.join(MPV_DIRECTORY, "mpv.conf")

    if os.path.exists(anime4k_shader_path):
        print(f"Removing: {anime4k_shader_path}")
        shutil.rmtree(anime4k_shader_path)

    if os.path.exists(anime4k_input_conf_path):
        print(f"Removing: {anime4k_input_conf_path}")
        os.remove(anime4k_input_conf_path)

    if os.path.exists(anime4k_mpv_conf_path):
        print(f"Removing: {anime4k_mpv_conf_path}")
        os.remove(anime4k_mpv_conf_path)


def remove_mpv_scripts():
    scripts = ["aniskip.lua", "autoexit.lua", "autostart.lua"]

    for script in scripts:
        script_path = os.path.join(MPV_DIRECTORY, "scripts", script)
        if os.path.exists(script_path):
            print(f"Removing: {script_path}")
            os.remove(script_path)


def copy_file_if_different(source_path, destination_path):
    if os.path.exists(destination_path):
        with open(source_path, 'r', encoding="utf-8") as source_file:
            source_content = source_file.read()

        with open(destination_path, 'r', encoding="utf-8") as destination_file:
            destination_content = destination_file.read()

        if source_content != destination_content:
            logging.debug(
                "Content differs, overwriting %s", os.path.basename(
                    destination_path
                )
            )
            shutil.copy(source_path, destination_path)
        else:
            logging.debug(
                "%s already exists and is identical, no overwrite needed",
                os.path.basename(destination_path)
            )
    else:
        logging.debug(
            "Copying %s to %s",
            os.path.basename(source_path),
            os.path.dirname(destination_path)
        )
        shutil.copy(source_path, destination_path)


def setup_autostart():
    script_directory = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    mpv_scripts_directory = MPV_SCRIPTS_DIRECTORY

    if not os.path.exists(mpv_scripts_directory):
        os.makedirs(mpv_scripts_directory)

    autostart_source_path = os.path.join(
        script_directory, 'aniskip', 'scripts', 'autostart.lua'
    )

    autostart_destination_path = os.path.join(
        mpv_scripts_directory, 'autostart.lua'
    )

    logging.debug("Copying %s to %s if needed.",
                  autostart_source_path, autostart_destination_path)
    copy_file_if_different(autostart_source_path, autostart_destination_path)


def setup_autoexit():
    logging.debug("Copying autoexit.lua to mpv script directory")
    script_directory = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    mpv_scripts_directory = MPV_SCRIPTS_DIRECTORY

    if not os.path.exists(mpv_scripts_directory):
        os.makedirs(mpv_scripts_directory)

    autoexit_source_path = os.path.join(
        script_directory, 'aniskip', 'scripts', 'autoexit.lua')
    autoexit_destination_path = os.path.join(
        mpv_scripts_directory, 'autoexit.lua')

    copy_file_if_different(autoexit_source_path, autoexit_destination_path)


if __name__ == "__main__":
    print(check_avx2_support())
