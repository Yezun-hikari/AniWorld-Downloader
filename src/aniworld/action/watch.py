import subprocess
import logging

from aniworld.aniskip import aniskip
from aniworld.common import download_mpv
from aniworld.config import MPV_PATH, PROVIDER_HEADERS, INVALID_PATH_CHARS
from aniworld.models import Anime
from aniworld.parser import arguments


def _build_watch_command(source, media_title=None, headers=None, aniskip_data=None, anime=None):
    command = [MPV_PATH, source, "--fs", "--quiet"]
    if media_title:
        command.append(f'--force-media-title="{media_title}"')
    if headers:
        if anime.provider != "Luluvdo":
            for header in headers:
                command.append(f"--http-header-fields={header}")
        else:
            command.append(f"--http-header-fields={headers[0]}")
    if aniskip_data:
        command.extend(aniskip_data.split()[:2])
    return command


def _print_or_run(title, command):
    if arguments.only_command:
        print(f"\n{title}:")
        print(" ".join(str(item) for item in command if item is not None))
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


def _process_local_files():
    for file in arguments.local_episodes:
        command = _build_watch_command(file)
        _print_or_run(file, command)


def _process_anime_episodes(anime):
    for episode in anime:
        if arguments.only_direct_link:
            print(
                f"{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):")
            print(f"{episode.get_direct_link()}\n")
            continue

        sanitized_anime_title = ''.join(
            char for char in anime.title if char not in INVALID_PATH_CHARS
        )

        if episode.season == 0:
            media_title = (
                f"{sanitized_anime_title} - "
                f"Movie {episode.episode:02} - "
                f"({anime.language})"
            )
        else:
            media_title = (
                f"{sanitized_anime_title} - "
                f"S{episode.season:02}E{episode.episode:03} - "
                f"({anime.language})"
            )

        title = _generate_episode_title(anime, episode)
        command = _build_watch_command(
            episode.get_direct_link(),
            media_title,
            PROVIDER_HEADERS.get(anime.provider),
            aniskip(anime.title, episode.episode,
                    episode.season, episode.season_episode_count[episode.season])
            if anime.aniskip else None,
            anime
        )
        _print_or_run(title, command)


def _generate_episode_title(anime, episode):
    if episode.has_movies and episode.season not in episode.season_episode_count:
        return f"{anime.title} - Movie {episode.episode} - {episode.title_german}"
    return f"{anime.title} - S{episode.season}E{episode.episode} - {episode.title_german}"


def watch(anime: Anime = None):
    download_mpv()

    if anime is None:
        _process_local_files()
    else:
        _process_anime_episodes(anime)
