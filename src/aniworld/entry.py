import traceback
import logging
import sys

from aniworld.ascii_art import display_traceback_art
from aniworld.action import watch, syncplay
from aniworld.models import Anime, Episode
from aniworld.parser import arguments
from aniworld.search import search_anime
from aniworld.execute import execute
from aniworld.menu import menu
from aniworld.common import generate_links


def aniworld() -> None:  # pylint: disable=too-many-branches, too-many-statements
    try:
        if arguments.local_episodes:
            if arguments.action == "Watch":
                watch(None)
            elif arguments.action == "Syncplay":
                syncplay(None)
        if arguments.episode or arguments.episode_file:
            links = []
            if arguments.episode_file:
                try:
                    with open(arguments.episode_file, 'r', encoding="UTF-8") as file:
                        urls = []
                        for line in file:
                            line = line.strip()
                            if line.startswith("http"):
                                urls.append(line)

                        links.extend(urls)
                except FileNotFoundError:
                    logging.error(
                        "The specified episode file does not exist: %s", arguments.episode_file
                    )
                    sys.exit(1)
                except IOError as e:
                    logging.error("Error reading the episode file: %s", e)
                    sys.exit(1)

            if arguments.episode:
                links.extend(arguments.episode)
            links = generate_links(links, arguments)

            anime_list = []
            episode_list = []
            current_anime = None
            for link in (links or [None]):
                if link:
                    parts = link.split('/')
                    series_slug = parts[parts.index("stream") + 1]

                    if series_slug != current_anime:
                        if episode_list:
                            anime_list.append(Anime(episode_list=episode_list))
                            episode_list = []
                        current_anime = series_slug

                    episode_list.append(Episode(link=link))

                else:
                    slug = arguments.slug or search_anime()
                    episode = Episode(slug=slug)
                    anime_list.append(Anime(episode_list=[episode]))

            if episode_list:
                anime_list.append(Anime(episode_list=episode_list))

            execute(anime_list=anime_list)
        if not arguments.episode and not arguments.local_episodes and not arguments.episode_file:
            while True:
                try:
                    slug = arguments.slug if arguments.slug else search_anime()
                    break
                except ValueError:
                    continue

            anime = menu(arguments=arguments, slug=slug)
            execute(anime_list=[anime])
    except KeyboardInterrupt:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
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


if __name__ == "__main__":
    aniworld()
