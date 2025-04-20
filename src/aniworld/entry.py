import traceback

from aniworld.action import watch, syncplay
from aniworld.models import Anime, Episode
from aniworld.parser import arguments
from aniworld.search import search_anime
from aniworld.execute import execute
from aniworld.menu import menu


def aniworld() -> None:
    try:
        if arguments.local_episodes:
            if arguments.action == "Watch":
                watch(None)
            elif arguments.action == "Syncplay":
                syncplay(None)
        if arguments.episode:
            # TODO: this needs to pass all links to a function
            #       that will return Anime objects instead
            anime_list = []
            for link in (arguments.episode or [None]):
                if link:
                    episode = Episode(
                        link=link
                    )
                else:
                    slug = arguments.slug if arguments.slug else search_anime()
                    episode = Episode(
                        slug=slug
                    )
                anime = Anime(episode_list=[episode])
                anime_list.append(anime)

            execute(anime_list=anime_list)
        if not arguments.episode and not arguments.local_episodes:
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
    except Exception as e:
        if arguments.debug:
            traceback.print_exc()
        else:
            # hide traceback only show output
            print(str(e))


if __name__ == "__main__":
    aniworld()
