import logging
import os
import pathlib
import platform
import shutil
import tempfile

from importlib.metadata import PackageNotFoundError, version
from urllib3.exceptions import InsecureRequestWarning
import urllib3
from fake_useragent import UserAgent

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
logging.getLogger().setLevel(logging.WARNING)

urllib3.disable_warnings(InsecureRequestWarning)

#########################################################################################
# Default Configuration Constants
#########################################################################################

try:
    VERSION = version('aniworld')
except PackageNotFoundError:
    VERSION = ""

IS_NEWEST_VERSION = True  # For now :)
PLATFORM_SYSTEM = platform.system()

SUPPORTED_PROVIDERS = [
    "VOE", "Doodstream", "Vidmoly", "Vidoza", "SpeedFiles", "Streamtape", "Luluvdo"
]

LULUVDO_USER_AGENT = "Mozilla/5.0 (Android 15; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0"

PROVIDER_HEADERS = {
    "Vidmoly": 'Referer: "https://vidmoly.to"',
    "Doodstream": 'Referer: "https://dood.li/"',
    "VOE": 'Referer: "https://nathanfromsubject.com/"',
    "Luluvdo": f'User-Agent: {LULUVDO_USER_AGENT}'
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
DEFAULT_PROVIDER_WATCH = "Doodstream"
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_TERMINAL_SIZE = (90, 30)

# https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
INVALID_PATH_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '&']


#########################################################################################
# User Agents
#########################################################################################

RANDOM_USER_AGENT = UserAgent().random

#########################################################################################
# Executable Path Resolution
#########################################################################################

DEFAULT_APPDATA_PATH = os.getenv(
    "APPDATA"
) or os.path.expanduser("~/.aniworld")

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
