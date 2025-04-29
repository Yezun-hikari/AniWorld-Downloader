import argparse
import importlib
import json
import os
import logging
import platform
import random
import subprocess
import shutil
import sys

import requests

from aniworld.common import download_mpv, download_syncplay, remove_anime4k, remove_mpv_scripts
from aniworld.extractors import get_direct_link_from_hanime
from aniworld.anime4k import download_anime4k
from aniworld import config


class CaseInsensitiveChoices:  # pylint: disable=too-few-public-methods
    def __init__(self, choices):
        self.choices = choices
        self.normalized = {c.lower(): c for c in choices}

    def __call__(self, value):
        key = value.lower()
        if key in self.normalized:
            return self.normalized[key]
        raise argparse.ArgumentTypeError(
            f"invalid choice: {value} (choose from {', '.join(self.choices)})")


def get_random_anime_slug(genre) -> str:
    url = f'{config.ANIWORLD_TO}/ajax/randomGeneratorSeries'

    data = {
        'productionStart': 'all',
        'productionEnd': 'all', 'genres[]': genre
    }

    headers = {'User-Agent': config.RANDOM_USER_AGENT}

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=config.DEFAULT_REQUEST_TIMEOUT
        )

        response.raise_for_status()
        anime_list = response.json()

        if not anime_list:
            logging.warning("No anime found for genre: %s", genre)
            return None

        random_anime = random.choice(anime_list)
        logging.debug("Selected Anime: %s", random_anime)

        return random_anime.get('link')

    except requests.RequestException as e:
        logging.error("Request failed: %s", e)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logging.error("Error processing response: %s", e)

    return None


def parse_arguments() -> argparse.Namespace:  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    parser = argparse.ArgumentParser(
        description="Parse command-line arguments for anime streaming, "
                    "downloading, and playback management."
    )

    # General options
    general_opts = parser.add_argument_group('General Options')
    general_opts.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug mode for detailed logs.'
    )
    general_opts.add_argument(
        '-U', '--update',
        type=str,
        choices=['mpv', 'yt-dlp', 'syncplay', 'all'],
        help='Update specified tools (mpv, yt-dlp, syncplay, or all).'
    )
    general_opts.add_argument(
        '-u', '--uninstall',
        action='store_true',
        help='Perform self-uninstallation.'
    )
    general_opts.add_argument(
        '-v', '--version',
        action='store_true',
        help='Display version information.'
    )

    # Search options
    search_opts = parser.add_argument_group('Search Options')
    search_opts.add_argument(
        '-s', '--slug',
        type=str,
        help='Specify a search slug (e.g., demon-slayer-kimetsu-no-yaiba).'
    )

    # Episode options
    episode_opts = parser.add_argument_group('Episode Options')
    episode_opts.add_argument(
        '-e', '--episode',
        type=str,
        nargs='+',
        help='Specify one or more episode URLs.'
    )
    episode_opts.add_argument(
        '-f', '--episode-file',
        type=str,
        help='Provide a file containing episode URLs.'
    )
    episode_opts.add_argument(
        '-lf', '--local-episodes',
        type=str,
        nargs='+',
        help='Use local MP4 files for episodes instead of URLs.'
    )
    episode_opts.add_argument(
        '-pl', '--provider-link',
        type=str,
        nargs='+',
        help='Specify one or more provider episode urls.'
    )

    # Action options
    action_opts = parser.add_argument_group('Action Options')
    action_opts.add_argument(
        '-a', '--action',
        type=CaseInsensitiveChoices(['Watch', 'Download', 'Syncplay']),
        default=config.DEFAULT_ACTION,
        help='Specify the action to perform.'
    )
    action_opts.add_argument(
        '-o', '--output-dir',
        type=str,
        default=config.DEFAULT_DOWNLOAD_PATH,
        help='Set the download directory (e.g., /path/to/downloads).'
    )
    action_opts.add_argument(
        '-L', '--language',
        type=CaseInsensitiveChoices(
            ['German Dub', 'English Sub', 'German Sub']
        ),
        default=config.DEFAULT_LANGUAGE,
        help='Specify the language for playback or download.'
    )
    action_opts.add_argument(
        '-p', '--provider',
        type=CaseInsensitiveChoices(config.SUPPORTED_PROVIDERS),
        help='Specify the preferred provider.'
    )

    # Anime4K options
    anime4k_opts = parser.add_argument_group('Anime4K Options')
    anime4k_opts.add_argument(
        '-A', '--anime4k',
        type=CaseInsensitiveChoices(['High', 'Low', 'Remove']),
        help='Set Anime4K mode (High, Low, or Remove for performance tuning).'
    )

    # Syncplay options
    syncplay_opts = parser.add_argument_group('Syncplay Options')
    syncplay_opts.add_argument(
        '-sH', '--hostname',
        type=str,
        help='Set the Syncplay server hostname.'
    )
    syncplay_opts.add_argument(
        '-sU', '--username',
        type=str,
        help='Set the Syncplay username.'
    )
    syncplay_opts.add_argument(
        '-sR', '--room',
        type=str,
        help='Specify the Syncplay room name.'
    )
    syncplay_opts.add_argument(
        '-sP', '--password',
        type=str,
        nargs='+',
        help='Set the Syncplay room password.'
    )

    # Miscellaneous options
    misc_opts = parser.add_argument_group('Miscellaneous Options')
    misc_opts.add_argument(
        '-k', '--aniskip',
        action='store_true',
        help='Skip anime intros and outros using Aniskip.'
    )
    misc_opts.add_argument(
        '-K', '--keep-watching',
        action='store_true',
        help='Automatically continue to the next episodes after the selected one.'
    )
    misc_opts.add_argument(
        '-r', '--random-anime',
        type=str,
        nargs='*',
        help='Play a random anime (default genre is "all", e.g., Drama).\n'
             f'All genres can be found here: "{config.ANIWORLD_TO}/random"'
    )
    misc_opts.add_argument(
        '-D', '--only-direct-link',
        action='store_true',
        help='Output only the direct streaming link.'
    )
    misc_opts.add_argument(
        '-C', '--only-command',
        action='store_true',
        help='Output only the execution command.'
    )

    args = parser.parse_args()

    if args.uninstall:
        print(f"Removing: {config.DEFAULT_APPDATA_PATH}")
        if os.path.exists(config.DEFAULT_APPDATA_PATH):
            shutil.rmtree(config.DEFAULT_APPDATA_PATH)

        remove_anime4k()
        remove_mpv_scripts()

        if sys.platform.startswith('win'):
            command = "timeout 3 >nul & pip uninstall -y aniworld"
        else:
            command = "pip uninstall -y aniworld"

        print("pip uninstall -y aniworld")
        subprocess.Popen(  # pylint: disable=consider-using-with
            command,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        sys.exit()

    if args.version:
        cowsay = fR"""
_____________________________
< AniWorld-Downloader v.{config.VERSION} >
-----------------------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||
"""
        if not config.IS_NEWEST_VERSION:
            cowsay += (
                f"\nYour version is outdated.\n"
                f"Please update to the latest version (v.{config.LATEST_VERSION})."
            )
        else:
            cowsay += "\nYou are on the latest version."
        print(cowsay.strip())
        sys.exit()

    if args.anime4k:
        download_anime4k(args.anime4k)

    if args.provider_link:  # pylint: disable=too-many-nested-blocks
        invalid_links = [
            link for link in args.provider_link if not link.startswith("http")
        ]
        if invalid_links:
            print(f"Invalid provider episode URLs: {', '.join(invalid_links)}")
            sys.exit(1)
        for link in args.provider_link:
            if link.startswith("https://hanime.tv/videos/"):
                get_direct_link_from_hanime(link)

        args.provider_link = [link for link in args.provider_link if not link.startswith(
            "https://hanime.tv/videos/")]

        if not args.provider_link:
            sys.exit()

        if not args.provider:
            print("Provider must be specified when using provider links.")
            sys.exit(1)

        logging.info("Using provider: %s", args.provider)

        if args.provider in config.SUPPORTED_PROVIDERS:
            module = importlib.import_module("aniworld.extractors")
            func = getattr(
                module, f"get_direct_link_from_{args.provider.lower()}"
            )

            for provider_episode in args.provider_link:
                direct_link = f'"{func(provider_episode)}"'

                if args.provider in config.PROVIDER_HEADERS:
                    if config.PROVIDER_HEADERS.get(args.provider):
                        action = (
                            config.YTDLP_PATH if args.action == "Download" else
                            config.MPV_PATH if args.action == "Watch" else
                            config.SYNCPLAY_PATH if args.action == "Syncplay" else
                            None
                        )

                        if action:
                            header = (
                                "--add-header"
                                if args.action == "Download"
                                else "--http-header-fields"
                            )
                            direct_link = (
                                f"{action} {direct_link} "
                                f"{header}='{config.PROVIDER_HEADERS[args.provider]}'"
                            )
                        else:
                            raise ValueError("Invalid action.")

                print(f"-> {provider_episode}")
                print(direct_link)
                print("-" * 40)

            sys.exit()

    if args.update:
        def update_yt_dlp():
            logging.info("Upgrading yt-dlp...")
            yt_dlp_update_command = ["pip", "install", "-U", "yt-dlp"]

            logging.debug("Running Command: %s", yt_dlp_update_command)
            subprocess.run(
                yt_dlp_update_command,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        def update_all():
            logging.info("Updating all tools...")
            download_mpv(update=True)
            update_yt_dlp()
            download_syncplay(update=True)

        update_actions = {
            "mpv": lambda: download_mpv(update=True),
            "yt-dlp": update_yt_dlp,
            "syncplay": lambda: download_syncplay(update=True),
            "all": update_all
        }

        action = update_actions.get(args.update)
        if action:
            action()
        else:
            logging.error("Invalid update option provided.")

    if args.random_anime is not None:
        args.slug = get_random_anime_slug(
            args.random_anime if len(args.random_anime) != 0 else "all")

    if args.provider is None:
        config.USES_DEFAULT_PROVIDER = True  # pylint: disable=global-statement

        args.provider = (
            config.DEFAULT_PROVIDER_DOWNLOAD
            if args.action == "Download" else config.DEFAULT_PROVIDER_WATCH
        )

    if args.debug is True:
        def open_terminal_with_command(command):
            if os.environ.get('DISPLAY'):
                terminal_emulators = [
                    ('gnome-terminal', ['gnome-terminal', '--',
                     'bash', '-c', f'{command}; exec bash']),
                    ('xterm', ['xterm', '-hold', '-e', command]),
                    ('konsole', ['konsole', '--hold', '-e', command])
                ]

                for terminal, cmd in terminal_emulators:
                    try:
                        subprocess.Popen(  # pylint: disable=consider-using-with
                            cmd
                        )
                        return
                    except FileNotFoundError:
                        logging.debug(
                            "%s not found, trying next option.", terminal
                        )
                    except subprocess.SubprocessError as e:
                        logging.error(
                            "Error opening terminal with %s: %s", terminal, e)

                logging.error(
                    "No supported terminal emulator found. "
                    "Install gnome-terminal, xterm, or konsole.")
            print("It looks like you are on a headless machine! "
                  "For advanced log look in your temp folder!")
            return

        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("=============================================")
        logging.debug(
            "   Welcome to AniWorld Downloader v.%s!   ", config.VERSION)
        logging.debug("=============================================\n")

        system = platform.system()

        if system == "Darwin":
            try:
                darwin_open_debug_log = [
                    "osascript", "-e",
                    'tell application "Terminal" to do script "trap exit SIGINT; '
                    'tail -f -n +1 $TMPDIR/aniworld.log" activate'
                ]
                logging.debug("Running Command: %s", darwin_open_debug_log)
                subprocess.run(darwin_open_debug_log, check=True)
            except subprocess.CalledProcessError as e:
                logging.error("Failed to start tailing the log file: %s", e)
        elif system == "Windows":
            try:
                windows_open_debug_log = (
                    "start cmd /c \"powershell -NoExit -c "
                    "Get-Content -Wait \"$env:TEMP\\aniworld.log\"\""
                )
                logging.debug("Running Command: %s", windows_open_debug_log)
                subprocess.run(windows_open_debug_log, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                logging.error("Failed to start tailing the log file: %s", e)
        elif system == "Linux":
            open_terminal_with_command('tail -f -n +1 /tmp/aniworld.log')

    return args


arguments = parse_arguments()

if __name__ == "__main__":
    pass
