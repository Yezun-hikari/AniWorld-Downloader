import logging
import os
import pathlib
import platform
import shutil
import tempfile
from importlib.metadata import PackageNotFoundError, version
from packaging.version import Version, InvalidVersion
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import requests
from fake_useragent import UserAgent


#########################################################################################
# Global Constants
#########################################################################################

ANIWORLD_TO = "https://aniworld.to"
S_TO = "https://s.to"

#########################################################################################
# Logging Configuration
#########################################################################################

log_file_path = os.path.join(tempfile.gettempdir(), 'aniworld.log')


class CriticalErrorHandler(logging.Handler):
    def emit(self, record):
        if record.levelno == logging.CRITICAL:
            raise SystemExit(record.getMessage())


logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s:%(name)s:%(funcName)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, mode='w'),
        CriticalErrorHandler()
    ]
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter(
    "%(levelname)s:%(name)s:%(funcName)s: %(message)s")
)
logging.getLogger().addHandler(console_handler)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger('charset_normalizer').setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.WARNING)

urllib3.disable_warnings(InsecureRequestWarning)

#########################################################################################
# Default Configuration Constants
#########################################################################################

DEFAULT_REQUEST_TIMEOUT = 30

try:
    VERSION = version('aniworld')
except PackageNotFoundError:
    VERSION = ""


def get_latest_github_version():
    try:
        url = "https://api.github.com/repos/phoenixthrush/AniWorld-Downloader/releases/latest"
        response = requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
        return response.json().get('tag_name', '') if response.status_code == 200 else ""
    except requests.RequestException as e:
        logging.error("Error fetching latest release: %s", e)
        return ""


def is_newest_version():
    try:
        current = Version(VERSION.lstrip('v').lstrip('.'))
        latest_str = get_latest_github_version().lstrip('v').lstrip('.')
        latest = Version(latest_str)
        return latest, current >= latest
    except InvalidVersion as e:
        logging.error("Invalid version format: %s", e)
    except requests.RequestException as e:
        logging.error("Network error while fetching latest version: %s", e)

    return False


try:
    LATEST_VERSION, IS_NEWEST_VERSION = is_newest_version()
except TypeError:  # GitHub API Rate Limit (60/h) #52
    LATEST_VERSION = VERSION
    IS_NEWEST_VERSION = True

PLATFORM_SYSTEM = platform.system()

SUPPORTED_PROVIDERS = [
    "LoadX", "VOE", "Vidmoly", "Luluvdo", "Doodstream", "Vidoza", "SpeedFiles", "Streamtape"
    # , "Filemoon"
]

#########################################################################################
# User Agents
#########################################################################################

RANDOM_USER_AGENT = UserAgent().random

LULUVDO_USER_AGENT = "Mozilla/5.0 (Android 15; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0"

PROVIDER_HEADERS_D = {
    "Vidmoly": ['Referer: "https://vidmoly.to"'],
    "Doodstream": ['Referer: "https://dood.li/"'],
    "VOE": [f'User-Agent: {RANDOM_USER_AGENT}'],
    "LoadX": ['Accept: */*'],
    "Luluvdo": [
        f'User-Agent: {LULUVDO_USER_AGENT}',
        'Accept-Language: de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin: "https://luluvdo.com"',
        'Referer: "https://luluvdo.com/"'
    ]}

PROVIDER_HEADERS_W = {
    "Vidmoly": ['Referer: "https://vidmoly.to"'],
    "Doodstream": ['Referer: "https://dood.li/"'],
    "VOE": [f'User-Agent: {RANDOM_USER_AGENT}'],
    "Luluvdo": [f'User-Agent: {LULUVDO_USER_AGENT}']
}


USES_DEFAULT_PROVIDER = False

# E.g. Watch, Download, Syncplay
DEFAULT_ACTION = "Download"
DEFAULT_ANISKIP = False
DEFAULT_DOWNLOAD_PATH = pathlib.Path.home() / "Downloads"
DEFAULT_KEEP_WATCHING = False
# German Dub, English Sub, German Sub
DEFAULT_LANGUAGE = "German Sub"
DEFAULT_ONLY_COMMAND = False
DEFAULT_ONLY_DIRECT_LINK = False
# SUPPORTED_PROVIDERS above
DEFAULT_PROVIDER_DOWNLOAD = "VOE"
DEFAULT_PROVIDER_WATCH = "Vidmoly"
DEFAULT_TERMINAL_SIZE = (90, 30)

# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
INVALID_PATH_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '&']

#########################################################################################
# Executable Path Resolution
#########################################################################################

DEFAULT_APPDATA_PATH = os.path.join(
    os.getenv("APPDATA") or os.path.expanduser("~"), "aniworld"
)

if os.name == 'nt':
    MPV_DIRECTORY = os.path.join(os.environ.get('APPDATA', ''), 'mpv')
else:
    MPV_DIRECTORY = os.path.expanduser('~/.config/mpv')

MPV_SCRIPTS_DIRECTORY = os.path.join(MPV_DIRECTORY, 'scripts')

if platform.system() == "Windows":
    mpv_path = shutil.which("mpv")
    if not mpv_path:
        mpv_path = os.path.join(os.getenv('APPDATA', ''),
                                "aniworld", "mpv", "mpv.exe")
else:
    mpv_path = shutil.which("mpv")

MPV_PATH = mpv_path

if platform.system() == "Windows":
    syncplay_path = shutil.which("syncplay")
    if syncplay_path:
        syncplay_path = syncplay_path.replace(
            "syncplay.EXE", "SyncplayConsole.exe")
    else:
        syncplay_path = os.path.join(
            os.getenv(
                'APPDATA', ''), "aniworld", "syncplay", "SyncplayConsole.exe"
        )
else:
    syncplay_path = shutil.which("syncplay")

SYNCPLAY_PATH = syncplay_path

YTDLP_PATH = shutil.which("yt-dlp")  # already in pip deps

#########################################################################################

if __name__ == '__main__':
    pass
