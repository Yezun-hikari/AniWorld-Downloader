import sys
import logging
from typing import List, Dict, Callable

from aniworld.models import Anime
from aniworld.action import watch, download, syncplay


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


def _execute_single_anime(anime: Anime) -> bool:
    """
    Execute action for a single anime.

    Args:
        anime: The anime object to process

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        _validate_anime(anime)
        action_func = ACTION_MAP[anime.action]
        action_func(anime)
        logging.debug(
            "Successfully executed %s for anime: %s",
            anime.action,
            getattr(anime, "title", "Unknown"),
        )
        return True

    except AttributeError as e:
        logging.error("Anime object missing required attributes: %s", e)
        return False

    except ValueError as e:
        logging.error("Invalid action configuration: %s", e)
        return False

    except Exception as e:
        logging.error("Unexpected error executing %s for anime: %s", anime.action, e)
        return False


def execute(anime_list: List[Anime]) -> None:
    """
    Execute actions for a list of anime objects.

    Args:
        anime_list: List of anime objects to process

    Raises:
        SystemExit: If no anime could be processed successfully
    """
    if not anime_list:
        logging.warning("No anime provided to execute")
        return

    successful_executions = 0
    total_anime = len(anime_list)

    for i, anime in enumerate(anime_list, 1):
        logging.debug("Processing anime %d/%d", i, total_anime)

        if _execute_single_anime(anime):
            successful_executions += 1

    if successful_executions == 0:
        logging.error("Failed to execute any anime actions")
        sys.exit(1)
    elif successful_executions < total_anime:
        logging.warning(
            "Successfully executed %d/%d anime actions",
            successful_executions,
            total_anime,
        )
    else:
        logging.debug("Successfully executed all %d anime actions", total_anime)
