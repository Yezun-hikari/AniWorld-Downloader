from aniworld.entry import aniworld
from aniworld.config import VERSION


def main():
    print(f"\033]0;AniWorld-Downloader {VERSION}\007", end='', flush=True)
    aniworld()


if __name__ == "__main__":
    main()
