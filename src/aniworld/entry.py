import traceback
import logging
import sys
from typing import List, Union

from .ascii_art import display_traceback_art
from .action import watch, syncplay
from .models import Anime, Episode, SUPPORTED_SITES, Movie
from .parser import arguments
from .search import search_media
from .execute import execute
from .menu import menu
from .common import generate_links
from .config import S_TO, MEGAKINO_URL


def _detect_site_from_url(url: str) -> str:
    """
    Detect the streaming site from a URL.

    Args:
        url: The episode URL

    Returns:
        Site identifier (ANIWORLD_TO, S_TO, etc.)
    """
    for site, config in SUPPORTED_SITES.items():
        base_url = config["base_url"]
        if url.startswith(base_url):
            return site

    # Default to aniworld.to for backward compatibility
    return "aniworld.to"


def _handle_local_episodes() -> None:
    """Handle local episode playback."""
    if arguments.action == "Watch":
        watch(None)
    elif arguments.action == "Syncplay":
        syncplay(None)


def _read_episode_file(episode_file: str) -> List[str]:
    """Read episode URLs from a file."""
    try:
        with open(episode_file, "r", encoding="UTF-8") as file:
            # Use list comprehension for better performance
            urls = [line.strip() for line in file if line.strip().startswith("http")]
            return urls
    except FileNotFoundError:
        logging.error("The specified episode file does not exist: %s", episode_file)
        sys.exit(1)
    except IOError as err:
        logging.error("Error reading the episode file: %s", err)
        sys.exit(1)


def _collect_episode_links() -> List[str]:
    """Collect episode links from arguments and files."""
    links = []

    if arguments.episode_file:
        urls = _read_episode_file(arguments.episode_file)
        links.extend(urls)

    if arguments.episode:
        links.extend(arguments.episode)

    # Convert s.to links to config.S_TO IP for now
    links = [
        link.replace("http://s.to", S_TO).replace("https://s.to", S_TO)
        for link in links
    ]

    links = [link.rstrip("/") for link in links]

    return generate_links(links, arguments)


def _group_episodes_by_series(links: List[str]) -> List[Union[Anime, Movie]]:
    """Group episodes by series and create Anime objects."""
    if not links:
        return []

    media_list = []
    episode_list = []
    current_anime = None

    for link in links:
        if link:
            if MEGAKINO_URL in link:
                from .models import Movie
                # This is a movie, create a Movie object.
                # We need to get the title from the URL or a placeholder
                title = link.split("/")[-1] # Basic title from slug
                media_list.append(Movie(title=title, link=link))
                continue

            parts = link.split("/")
            try:
                series_slug = parts[parts.index("stream") + 1]
            except (ValueError, IndexError):
                logging.warning("Invalid episode link format: %s", link)
                continue

            site = _detect_site_from_url(link)

            if series_slug != current_anime:
                if episode_list:
                    # Get the site from the first episode in the list
                    episode_site = (
                        episode_list[0].site if episode_list else "aniworld.to"
                    )
                    media_list.append(
                        Anime(episode_list=episode_list, site=episode_site)
                    )
                    episode_list = []
                current_anime = series_slug

            episode_list.append(Episode(link=link, site=site))

    if episode_list:
        # Get the site from the first episode in the list
        episode_site = episode_list[0].site if episode_list else "aniworld.to"
        media_list.append(Anime(episode_list=episode_list, site=episode_site))

    # Handle case when no links are provided but we need to create a default anime
    if not media_list and not links:
        selected_media = search_media()
        if selected_media is None:
            return []
        slug = selected_media['link']
        if selected_media["type"] == "movie":
            from .models import Movie
            media_list.append(Movie(title=selected_media["name"], link=slug))
        else:
            episode = Episode(slug=slug)
            media_list.append(Anime(episode_list=[episode]))

    return media_list


def _handle_episode_mode() -> None:
    """Handle episode/file mode execution."""
    links = _collect_episode_links()

    # If no links were collected, handle as interactive mode
    if not links:
        media_list = _group_episodes_by_series(links)
    else:
        media_list = _group_episodes_by_series(links)

    execute(media_list=media_list)


def _handle_interactive_mode() -> None:
    """Handle interactive menu mode."""
    slug = arguments.slug

    if not slug:
        while True:
            try:
                selected_media = search_media()
                if selected_media is None:  # Handle menu cancellation
                    return
                if selected_media.get("type") == "movie":
                    from .models import Movie
                    movie = Movie(title=selected_media["name"], link=selected_media["link"])
                    execute(media_list=[movie])
                    return
                else:
                    slug = selected_media["link"]
                break
            except ValueError:
                continue

    anime = menu(arguments=arguments, slug=slug)
    execute(media_list=[anime])


def _handle_runtime_error(e: Exception) -> None:
    """Handle runtime errors with proper formatting."""
    if arguments.debug:
        traceback.print_exc()
    else:
        # hide traceback only show output
        print(display_traceback_art())
        print(f"Error: {e}")
        print("\nFor more detailed information, use --debug and try again.")

    # Detecting Nuitka at run time
    if "__compiled__" in globals():
        input("Press Enter to exit...")


def aniworld() -> None:
    """
    Main entry point for the AniWorld downloader.

    This function handles four main execution modes:
    1. Web UI mode - starts Flask web interface
    2. Local episodes mode - plays local video files
    3. Episode/file mode - processes specific episodes or episode files
    4. Interactive mode - presents a menu for anime selection

    Raises:
        KeyboardInterrupt: When user interrupts execution with Ctrl+C
        Exception: Any other runtime errors are caught and handled gracefully
    """
    try:
        # Handle web UI mode
        if arguments.web_ui:
            from .web.app import start_web_interface

            start_web_interface(
                arguments, port=arguments.web_port, debug=arguments.debug
            )
            return

        # Handle local episodes
        if arguments.local_episodes:
            _handle_local_episodes()
            return

        # Handle episode/file mode
        if arguments.episode or arguments.episode_file:
            _handle_episode_mode()
            return

        # Handle interactive mode (default)
        _handle_interactive_mode()

    except KeyboardInterrupt:
        pass
    except Exception as err:
        _handle_runtime_error(err)


if __name__ == "__main__":
    aniworld()
