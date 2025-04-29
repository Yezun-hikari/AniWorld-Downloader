from aniworld.entry import aniworld
from aniworld.config import VERSION, IS_NEWEST_VERSION


def main():
    print(
        f"\033]0;AniWorld-Downloader v.{VERSION}"
        f"{' (Update Available)' if not IS_NEWEST_VERSION else ''}\007",
        end='',
        flush=True
    )

    aniworld()


if __name__ == "__main__":
    main()
