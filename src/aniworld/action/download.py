import re
import subprocess
import logging
from pathlib import Path
from typing import Optional, List

from aniworld.models import Anime
from aniworld.config import PROVIDER_HEADERS_D, INVALID_PATH_CHARS
from aniworld.parser import arguments


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    return "".join(char for char in filename if char not in INVALID_PATH_CHARS)


def _format_episode_title(anime: Anime, episode) -> str:
    """Format episode title for logging."""
    return f"{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):"


def _get_output_filename(anime: Anime, episode, sanitized_title: str) -> str:
    """Generate output filename based on episode type."""
    if episode.season == 0:
        return (
            f"{sanitized_title} - Movie {episode.episode:03} - ({anime.language}).mp4"
        )
    return f"{sanitized_title} - S{episode.season:02}E{episode.episode:03} - ({anime.language}).mp4"


def _build_ytdl_command(direct_link: str, output_path: str, anime: Anime) -> List[str]:
    """Build yt-dlp command with all necessary parameters."""
    command = [
        "yt-dlp",
        direct_link,
        "--fragment-retries",
        "infinite",
        "--concurrent-fragments",
        "4",
        "-o",
        output_path,
        "--quiet",
        "--no-warnings",
        "--progress",
    ]

    # Add provider-specific headers
    if anime.provider in PROVIDER_HEADERS_D:
        for header in PROVIDER_HEADERS_D[anime.provider]:
            command.extend(["--add-header", header])

    return command


def _cleanup_partial_files(output_dir: Path) -> None:
    """Clean up partial download files and empty directories."""
    if not output_dir.exists():
        return

    is_empty = True
    partial_pattern = re.compile(r"\.(part|ytdl|part-Frag\d+)$")

    for file_path in output_dir.iterdir():
        if partial_pattern.search(file_path.name):
            try:
                file_path.unlink()
            except OSError as e:
                logging.warning("Failed to remove partial file %s: %s", file_path, e)
        else:
            is_empty = False

    # Remove empty directory
    if is_empty:
        try:
            output_dir.rmdir()
        except OSError as e:
            logging.warning(
                "Failed to remove empty directory %s: %s", str(output_dir), e
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


def _execute_download(command: List[str], output_path: Path) -> bool:
    """Execute download command with error handling."""
    try:
        print(f"Downloading to {output_path}...")
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        logging.error("Error running command:\n%s", " ".join(command))
        return False
    except KeyboardInterrupt:
        logging.info("Download interrupted by user")
        _cleanup_partial_files(output_path.parent)
        raise


def download(anime: Anime) -> None:
    """Download all episodes of an anime."""
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

        # Generate output path
        output_file = _get_output_filename(anime, episode, sanitized_anime_title)
        output_path = Path(arguments.output_dir) / sanitized_anime_title / output_file

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build command
        command = _build_ytdl_command(direct_link, str(output_path), anime)

        # Handle command only mode
        if arguments.only_command:
            print(
                f"\n{anime.title} - S{episode.season}E{episode.episode} - ({anime.language}):"
            )
            print(" ".join(command))
            continue

        # Execute download
        _execute_download(command, output_path)
