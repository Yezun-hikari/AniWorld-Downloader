import getpass
import subprocess
import logging
import hashlib

from aniworld.models import Anime
from aniworld.config import MPV_PATH, PROVIDER_HEADERS_W, SYNCPLAY_PATH, INVALID_PATH_CHARS
from aniworld.common import download_mpv, download_syncplay, setup_autostart, setup_autoexit
from aniworld.aniskip import aniskip
from aniworld.parser import arguments


def _get_syncplay_username():
    return arguments.username or getpass.getuser()


def _get_syncplay_hostname():
    return arguments.hostname or "syncplay.pl:8997"


def _get_syncplay_room(title):
    if arguments.room:
        return arguments.room

    room = title
    password = arguments.password

    if password:
        room += f":{password}"

    room_hash = hashlib.sha256(room.encode('utf-8')).hexdigest()

    return f"AniWorld_Downloader.{room_hash}"


def _append_password(command, title):
    password = arguments.password

    if not password:
        return command

    password = f"{arguments.password}:{title}"
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    command.insert(9, "--password")
    command.insert(10, password_hash)
    return command


def _execute_command(command):
    if arguments.only_command:
        print("\n" + " ".join(str(item) for item in command))
        return
    try:
        logging.debug("Running Command:\n%s", command)
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(
            "Error running command: %s\nCommand: %s",
            e, ' '.join(
                str(item) if item is not None else '' for item in command)
        )


def _build_syncplay_command(source, title=None, headers=None, aniskip_data=None,
                            anime=None, media_title=None):
    command = [
        SYNCPLAY_PATH,
        "--no-gui",
        "--no-store",
        "--host", _get_syncplay_hostname(),
        "--room", _get_syncplay_room(title=title),
        "--name", _get_syncplay_username(),
        "--player-path", MPV_PATH,
        source,
        "--",
        "--fs"
    ]

    if media_title:
        command.append(f'--force-media-title="{media_title}"')

    command = _append_password(command, title)

    if anime.provider == "Loadx":
        command.append("--demuxer=lavf")
        command.append("--demuxer-lavf-format=hls")

    if headers:
        for header in headers:
            command.append(f"--http-header-fields={header}")

    if aniskip_data:
        command.extend(aniskip_data.split()[:2])

    return command


def _process_anime_episodes(anime):
    for episode in anime:
        episode_title = f"{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):"
        direct_link = episode.get_direct_link()

        if not direct_link:
            logging.warning(f"Something went wrong with \"{episode_title}\".\n"
                            f"Error while trying to find a direct link.")
            continue

        if arguments.only_direct_link:
            print(
                episode_title
            )
            print(f"{direct_link}\n")
            continue

        sanitized_anime_title = ''.join(
            char for char in anime.title if char not in INVALID_PATH_CHARS
        )

        if episode.season == 0:
            media_title = (
                f"{sanitized_anime_title} - "
                f"Movie {episode.episode:03} - "
                f"({anime.language})"
            )
        else:
            media_title = (
                f"{sanitized_anime_title} - "
                f"S{episode.season:02}E{episode.episode:03} - "
                f"({anime.language})"
            )

        command = _build_syncplay_command(
            direct_link,
            episode.title_german,
            PROVIDER_HEADERS_W.get(anime.provider),
            aniskip(anime.title, episode.episode,
                    episode.season, episode.season_episode_count[episode.season])
            if anime.aniskip else None,
            anime,
            media_title
        )
        _execute_command(command)


def _process_local_files():
    for file in arguments.local_episodes:
        command = _build_syncplay_command(file)
        _execute_command(command)


def syncplay(anime: Anime = None):
    download_mpv()
    download_syncplay()

    setup_autostart()
    setup_autoexit()

    if anime is None:
        _process_local_files()
    else:
        _process_anime_episodes(anime)


if __name__ == '__main__':
    download_syncplay()
