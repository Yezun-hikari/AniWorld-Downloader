import os
import platform
import logging
import subprocess
import shutil

from aniworld.config import MPV_DIRECTORY
from aniworld.common import get_github_release, download_file, remove_anime4k


def get_anime4k_download_link(mode: str = "High") -> str:
    os_type = "Windows" if platform.system() == "Windows" else "Mac_Linux"

    latest_release = get_github_release("Tama47/Anime4K")
    download_path = os.path.dirname(list(latest_release.values())[0])
    download_link = f"{download_path}/GLSL_{os_type}_{mode}-end.zip"

    return download_link


def download_anime4k(mode):
    if mode == "Remove":
        remove_anime4k()
        return

    os.makedirs(MPV_DIRECTORY, exist_ok=True)
    archive_path = os.path.join(MPV_DIRECTORY, "anime4k.zip")

    if not os.path.exists(archive_path):
        download_link = get_anime4k_download_link(mode)
        print("Downloading Anime4K...")
        download_file(download_link, archive_path)

        extract_anime4k(zip_path=archive_path, dep_path=MPV_DIRECTORY)
    else:
        logging.warning("File already exists at: %s", archive_path)


def extract_anime4k(zip_path, dep_path):
    logging.debug("Unpacking Anime4K to %s", dep_path)
    try:
        subprocess.run(
            ["tar", "-xf", zip_path],
            check=True,
            cwd=dep_path
        )
    except subprocess.CalledProcessError as e:
        logging.error("Failed to extract files: %s", e)
    except subprocess.SubprocessError as e:
        logging.error("An error occurred: %s", e)

    if os.path.exists(zip_path):
        os.remove(zip_path)

    anime4k_path = os.path.join(MPV_DIRECTORY, "__MACOSX")
    if os.path.exists(anime4k_path):
        shutil.rmtree(anime4k_path)


if __name__ == "__main__":
    download_anime4k("High")
