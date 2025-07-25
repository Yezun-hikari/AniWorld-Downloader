import logging
from typing import Optional, List

from ..common import download_mpv
from ..config import MPV_PATH, PROVIDER_HEADERS_W
from ..models import Anime
from ..parser import arguments
from .common import (
    sanitize_filename,
    format_episode_title,
    get_media_title,
    get_direct_link,
    execute_command,
    get_aniskip_data,
)


def _build_watch_command(
    source: str,
    media_title: Optional[str] = None,
    headers: Optional[List[str]] = None,
    aniskip_data: Optional[str] = None,
    anime: Optional[Anime] = None,
) -> List[str]:
    """Build MPV watch command with all necessary parameters."""
    command = [MPV_PATH, source, "--fs", "--quiet"]

    if media_title:
        command.append(f'--force-media-title="{media_title}"')

    # Add provider-specific configurations
    if anime and anime.provider == "LoadX":
        command.extend(["--demuxer=lavf", "--demuxer-lavf-format=hls"])

    # Add headers
    if headers:
        for header in headers:
            command.append(f"--http-header-fields={header}")

    # Add aniskip data
    if aniskip_data:
        command.extend(aniskip_data.split()[:2])

    return command


def _process_local_files() -> None:
    """Process local files through MPV."""
    for file in arguments.local_episodes:
        command = _build_watch_command(source=file)
        execute_command(command=command)


def _process_anime_episodes(anime: Anime) -> None:
    """Process and watch all episodes of an anime through MPV."""
    sanitized_anime_title = sanitize_filename(anime.title)

    for episode in anime:
        episode_title = format_episode_title(anime, episode)

        # Get direct link
        direct_link = get_direct_link(episode, episode_title)
        if not direct_link:
            logging.warning(
                'Something went wrong with "%s".\nNo direct link found.', episode_title
            )
            continue

        # Handle direct link only mode
        if arguments.only_direct_link:
            print(episode_title)
            print(f"{direct_link}\n")
            continue

        # Generate titles
        media_title = get_media_title(anime, episode, sanitized_anime_title)
        # Get aniskip data
        aniskip_data = get_aniskip_data(anime, episode)

        # Build and execute command
        command = _build_watch_command(
            source=direct_link,
            media_title=media_title,
            headers=PROVIDER_HEADERS_W.get(anime.provider),
            aniskip_data=aniskip_data,
            anime=anime,
        )

        execute_command(command=command)


def watch(anime: Optional[Anime] = None) -> None:
    """Main watch function to setup and play anime or local files."""
    try:
        # Download required components
        download_mpv()

        # Process files
        if anime is None:
            _process_local_files()
        else:
            _process_anime_episodes(anime)

    except KeyboardInterrupt:
        logging.info("Watch session interrupted by user")
    except Exception as err:
        logging.error("Error in watch session: %s", err)
        raise
