import os
import re
import subprocess
import logging

from aniworld.models import Anime
from aniworld.config import PROVIDER_HEADERS_D, INVALID_PATH_CHARS
from aniworld.parser import arguments


def download(anime: Anime):  # pylint: disable=too-many-branches
    for episode in anime:
        episode_title = f"{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):"
        try:
            direct_link = episode.get_direct_link()
        except Exception as e:
            logging.warning(f"Something went wrong with \"{episode_title}\".\n"
                            f"Error while trying to find a direct link: {e}")
            continue

        if not direct_link:
            logging.warning(f"Something went wrong with \"{episode_title}\".\n"
                            f"Error while trying to find a direct link.")
            continue

        if arguments.only_direct_link:
            print(episode_title)
            print(f"{direct_link}\n")
            continue

        sanitized_anime_title = ''.join(
            char for char in anime.title if char not in INVALID_PATH_CHARS
        )

        if episode.season == 0:
            output_file = (
                f"{sanitized_anime_title} - "
                f"Movie {episode.episode:03} - "
                f"({anime.language}).mp4"
            )
        else:
            output_file = (
                f"{sanitized_anime_title} - "
                f"S{episode.season:02}E{episode.episode:03} - "
                f"({anime.language}).mp4"
            )

        output_path = os.path.join(
            arguments.output_dir, sanitized_anime_title, output_file
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        command = [
            "yt-dlp",
            direct_link,
            "--fragment-retries", "infinite",
            "--concurrent-fragments", "4",
            "-o", output_path,
            "--quiet",
            "--no-warnings",
            "--progress"
        ]

        if anime.provider in PROVIDER_HEADERS_D:
            for header in PROVIDER_HEADERS_D[anime.provider]:
                command.extend(["--add-header", header])

        if arguments.only_command:
            print(
                f"\n{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):"
            )
            print(
                f"{' '.join(str(item) if item is not None else '' for item in command)}"
            )
            continue

        try:
            print(f"Downloading to {output_path}...")
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            print(
                "Error running command:\n"
                f"{' '.join(str(item) if item is not None else '' for item in command)}"
            )
        except KeyboardInterrupt:
            # directory containing the output_path
            output_dir = os.path.dirname(output_path)
            is_empty = True

            # delete all .part, .ytdl, or .part-Frag followed by any number in output_path
            for file_name in os.listdir(output_dir):
                if re.search(r'\.(part|ytdl|part-Frag\d+)$', file_name):
                    os.remove(os.path.join(output_dir, file_name))
                else:
                    is_empty = False

            # delete folder too if empty after
            if is_empty or not os.listdir(output_dir):
                os.rmdir(output_dir)
