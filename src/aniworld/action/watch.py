import subprocess
import logging
from typing import Optional, List

from ..aniskip import aniskip
from ..common import download_mpv
from ..config import MPV_PATH, PROVIDER_HEADERS_W, INVALID_PATH_CHARS
from ..models import Anime
from ..parser import arguments


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    return "".join(char for char in filename if char not in INVALID_PATH_CHARS)


def _format_episode_title(anime: Anime, episode) -> str:
    """Format episode title for logging."""
    return f"{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):"


def _get_media_title(anime: Anime, episode, sanitized_title: str) -> str:
    """Generate media title for episode."""
    if episode.season == 0:
        return f"{sanitized_title} - Movie {episode.episode:03} - ({anime.language})"
    return f"{sanitized_title} - S{episode.season:02}E{episode.episode:03} - ({anime.language})"


def _generate_episode_title(anime: Anime, episode) -> str:
    """Generate display title for episode."""
    if episode.has_movies and episode.season not in episode.season_episode_count:
        return f"{anime.title} - Movie {episode.episode} - {episode.title_german}"
    return (
        f"{anime.title} - S{episode.season}E{episode.episode} - {episode.title_german}"
    )


def _get_direct_link(episode, episode_title: str) -> Optional[str]:
    """Get direct link for episode with error handling."""
    try:
        return episode.get_direct_link()
    except Exception as e:
        logging.warning(
            'Something went wrong with "%s".\nError while trying to find a direct link: %s',
            episode_title,
            e,
        )
        return None


def _get_aniskip_data(anime: Anime, episode) -> Optional[str]:
    """Get aniskip data for episode if enabled."""
    if not anime.aniskip:
        return None

    try:
        return aniskip(
            anime.title,
            episode.episode,
            episode.season,
            episode.season_episode_count[episode.season],
        )
    except Exception as e:
        logging.warning(
            "Failed to get aniskip data for %s: %s", anime.title, e)
        return None


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


def _execute_command(title: str, command: List[str]) -> None:
    """Execute command or print it if in command-only mode."""
    if arguments.only_command:
        print(f"\n{title}:")
        print(" ".join(str(item) for item in command))
        return

    try:
        logging.debug("Running Command:\n%s", command)
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logging.error("Error running command: %s\nCommand: %s",
                      e, " ".join(command))
    except KeyboardInterrupt:
        logging.info("Watch session interrupted by user")
        raise


def _process_local_files() -> None:
    """Process local files through MPV."""
    for file in arguments.local_episodes:
        command = _build_watch_command(source=file)
        _execute_command(title=file, command=command)


def _process_anime_episodes(anime: Anime) -> None:
    """Process and watch all episodes of an anime through MPV."""
    sanitized_anime_title = _sanitize_filename(anime.title)

    for episode in anime:
        episode_title = _format_episode_title(anime, episode)

        # Get direct link
        direct_link = _get_direct_link(episode, episode_title)
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
        media_title = _get_media_title(anime, episode, sanitized_anime_title)
        display_title = _generate_episode_title(anime, episode)

        # Get aniskip data
        aniskip_data = _get_aniskip_data(anime, episode)

        # Build and execute command
        command = _build_watch_command(
            source=direct_link,
            media_title=media_title,
            headers=PROVIDER_HEADERS_W.get(anime.provider),
            aniskip_data=aniskip_data,
            anime=anime,
        )

        _execute_command(title=display_title, command=command)


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
    except Exception as e:
        logging.error("Error in watch session: %s", e)
        raise
