import getpass
import subprocess
import logging

from aniworld.models import Anime
from aniworld.config import MPV_PATH, PROVIDER_HEADERS, SYNCPLAY_PATH
from aniworld.common import download_mpv, download_syncplay
from aniworld.aniskip import aniskip
from aniworld.parser import arguments


def _get_syncplay_username():
    return arguments.username or getpass.getuser()


def _get_syncplay_hostname():
    return arguments.hostname or "syncplay.pl:8997"


def _append_password(command):
    if arguments.password:
        command.extend(["--password", arguments.password])


def _execute_command(command):
    logging.debug("Executing command:\n%s", command)
    if arguments.only_command:
        print("\n" + " ".join(str(item) for item in command))
        return
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(
            "Error running command: %s\nCommand: %s",
            e, ' '.join(
                str(item) if item is not None else '' for item in command)
        )


def _build_syncplay_command(source, title=None, headers=None, aniskip_data=None):
    command = [
        SYNCPLAY_PATH,
        "--no-gui",
        "--no-store",
        "--host", _get_syncplay_hostname(),
        "--room", arguments.room or (title or source),
        "--name", _get_syncplay_username(),
        "--player-path", MPV_PATH,
        source,
        "--",
        "--fs"
    ]

    if title:
        command.append(f'--force-media-title="{title}"')
    _append_password(command)
    if headers:
        command.append(f"--http-header-fields={headers}")
    if aniskip_data:
        command.extend(aniskip_data.split()[:2])
    return command


def _process_anime_episodes(anime):
    for episode in anime:
        if arguments.only_direct_link:
            print(
                f"{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):")
            print(f"{episode.get_direct_link()}\n")
            continue

        command = _build_syncplay_command(
            episode.get_direct_link(),
            episode.title_german,
            PROVIDER_HEADERS.get(anime.provider),
            aniskip(anime.title, episode.episode,
                    episode.season) if anime.aniskip else None
        )
        _execute_command(command)


def syncplay(anime: Anime = None):
    download_mpv()
    download_syncplay()

    if anime is None:
        _process_local_files()
    else:
        _process_anime_episodes(anime)


if __name__ == '__main__':
    download_syncplay()
