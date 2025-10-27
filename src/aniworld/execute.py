import sys
import logging
from typing import List, Dict, Callable, Union

from .models import Anime, Movie
from .action import watch, download, syncplay
from .movie.action import download_movie


# Action mapping for better performance and maintainability
ACTION_MAP: Dict[str, Callable[[Anime], None]] = {
    "Watch": watch,
    "Download": download,
    "Syncplay": syncplay,
}


def _validate_anime(anime: Anime) -> None:
    """Validate anime object and its action."""
    if not hasattr(anime, "action") or anime.action is None:
        raise AttributeError(f"Anime object missing 'action' attribute: {anime}")

    if anime.action not in ACTION_MAP:
        valid_actions = ", ".join(ACTION_MAP.keys())
        raise ValueError(
            f"Invalid action '{anime.action}' for anime. Valid actions: {valid_actions}"
        )


def _execute_single_item(item: Union[Anime, Movie]) -> bool:
    """
    Execute action for a single anime or movie.

    Args:
        item: The anime or movie object to process

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if isinstance(item, Anime):
            _validate_anime(item)
            action_func = ACTION_MAP[item.action]
            action_func(item)
            logging.debug(
                "Successfully executed %s for anime: %s",
                item.action,
                getattr(item, "title", "Unknown"),
            )
        elif isinstance(item, Movie):
            download_movie(item)
            logging.debug(
                "Successfully executed download for movie: %s",
                getattr(item, "title", "Unknown"),
            )
        else:
            logging.error("Unsupported item type: %s", type(item))
            return False

        return True

    except AttributeError as err:
        logging.error("Item object missing required attributes: %s", err)
        return False

    except ValueError as err:
        logging.error("Invalid action configuration: %s", err)
        return False

    except Exception as err:
        logging.error("Unexpected error executing action for item: %s", err)
        return False


def execute(media_list: List[Union[Anime, Movie]]) -> None:
    """
    Execute actions for a list of anime or movie objects.

    Args:
        media_list: List of anime or movie objects to process

    Raises:
        SystemExit: If no anime could be processed successfully
    """
    if not anime_list:
        logging.warning("No anime provided to execute")
        return

    successful_executions = 0
    total_media = len(media_list)

    for i, item in enumerate(media_list, 1):
        logging.debug("Processing media %d/%d", i, total_media)

        if _execute_single_item(item):
            successful_executions += 1

    if successful_executions == 0:
        logging.error("Failed to execute any media actions")
        sys.exit(1)
    elif successful_executions < total_media:
        logging.warning(
            "Successfully executed %d/%d media actions",
            successful_executions,
            total_media,
        )
    else:
        logging.debug("Successfully executed all %d media actions", total_media)
