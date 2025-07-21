import json
import logging
import platform
import shutil
import subprocess
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

from aniworld.config import (
    DEFAULT_REQUEST_TIMEOUT,
    MPV_DIRECTORY,
    ANIWORLD_TO,
    MPV_SCRIPTS_DIRECTORY,
    DEFAULT_APPDATA_PATH,
    MPV_PATH,
    SYNCPLAY_PATH,
)

# Constants
PACKAGE_MANAGERS = {
    "apt": "sudo apt update && sudo apt install {}",
    "dnf": "sudo dnf install {}",
    "yum": "sudo yum install {}",
    "pacman": "sudo pacman -Sy {}",
    "zypper": "sudo zypper install {}",
    "apk": "sudo apk add {}",
    "xbps-install": "sudo xbps-install -S {}",
    "nix-env": "nix-env -iA nixpkgs.{}",
}


def _make_request(
    url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT
) -> requests.Response:
    """Make HTTP request with error handling."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        raise


def _run_command(
    command: List[str],
    cwd: Optional[str] = None,
    quiet: bool = True,
    shell: bool = False,
) -> bool:
    """Run shell command with error handling."""
    try:
        stdout = subprocess.DEVNULL if quiet else None
        stderr = subprocess.DEVNULL if quiet else None

        if shell and isinstance(command, list):
            command = " ".join(command)

        subprocess.run(
            command, check=True, cwd=cwd, stdout=stdout, stderr=stderr, shell=shell
        )
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {command} - {e}")
        return False
    except (FileNotFoundError, OSError) as e:
        logging.error(f"Command execution error: {e}")
        return False


def _detect_package_manager() -> Optional[str]:
    """Detect available package manager on Linux."""
    for pm in PACKAGE_MANAGERS:
        if shutil.which(pm):
            return pm
    return None


def _ensure_directory(path: str) -> None:
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)


def _remove_file_safe(file_path: str) -> None:
    """Safely remove file if it exists."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.debug(f"Removed file: {file_path}")
    except OSError as e:
        logging.warning(f"Failed to remove file {file_path}: {e}")


def _remove_directory_safe(dir_path: str) -> None:
    """Safely remove directory if it exists."""
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            logging.debug(f"Removed directory: {dir_path}")
    except OSError as e:
        logging.warning(f"Failed to remove directory {dir_path}: {e}")


def check_avx2_support() -> bool:
    """Check if CPU supports AVX2 instructions (Windows only)."""
    if platform.system() != "Windows":
        logging.debug("AVX2 check is only supported on Windows.")
        return False

    try:
        import cpuinfo  # type: ignore # pylint: disable=import-outside-toplevel

        info = cpuinfo.get_cpu_info()
        flags = info.get("flags", [])
        return "avx2" in flags
    except ImportError:
        logging.warning("cpuinfo package not available, assuming no AVX2 support")
        return False
    except Exception as e:
        logging.error(f"Error checking AVX2 support: {e}")
        return False


def get_github_release(repo: str) -> Dict[str, str]:
    """
    Get latest GitHub release assets.

    Args:
        repo: Repository in format 'owner/repo'

    Returns:
        Dictionary mapping asset names to download URLs
    """
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        response = _make_request(api_url)
        release_data = response.json()
        assets = release_data.get("assets", [])
        return {asset["name"]: asset["browser_download_url"] for asset in assets}
    except (json.JSONDecodeError, requests.RequestException) as e:
        logging.error(f"Failed to fetch release data from GitHub: {e}")
        return {}


def download_file(url: str, path: str) -> bool:
    """
    Download file with progress bar.

    Args:
        url: Download URL
        path: Destination path

    Returns:
        True if download successful
    """
    try:
        response = requests.get(
            url, stream=True, allow_redirects=True, timeout=DEFAULT_REQUEST_TIMEOUT
        )
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024

        with (
            open(path, "wb") as f,
            tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=f"Downloading {Path(path).name}",
            ) as pbar,
        ):
            for data in response.iter_content(block_size):
                f.write(data)
                pbar.update(len(data))

        logging.info(f"Successfully downloaded: {path}")
        return True

    except requests.RequestException as e:
        logging.error(f"Failed to download {url}: {e}")
        return False
    except OSError as e:
        logging.error(f"Failed to write file {path}: {e}")
        return False


def _download_7z(zip_tool: str) -> bool:
    """Download 7z tool for Windows."""
    if not os.path.exists(zip_tool):
        logging.info("Downloading 7z...")
        return download_file("https://7-zip.org/a/7zr.exe", zip_tool)
    return True


def _install_with_homebrew(package: str, update: bool = False) -> bool:
    """Install or update package using Homebrew."""
    if not shutil.which("brew"):
        return False

    if update:
        logging.info(f"Updating {package} using Homebrew...")
        success = _run_command(["brew", "update"])
        if success:
            success = _run_command(["brew", "upgrade", "--formula", package])
    else:
        if shutil.which(package):
            return True
        logging.info(f"Installing {package} using Homebrew...")
        success = _run_command(["brew", "update"])
        if success:
            success = _run_command(["brew", "install", "--formula", package])

    return success


def _install_with_package_manager(package: str) -> bool:
    """Install package using Linux package manager."""
    pm = _detect_package_manager()
    if not pm:
        logging.error("No supported package manager found")
        return False

    install_cmd = PACKAGE_MANAGERS[pm].format(package)
    logging.info(f"Installing {package} using {pm}...")
    return _run_command(
        install_cmd.split()
        if not any(op in install_cmd for op in ["&&", "||", ";"])
        else [install_cmd],
        shell=True,
    )


def _get_mpv_download_link(direct_links: Dict[str, str]) -> Optional[str]:
    """Get appropriate MPV download link based on CPU capabilities."""
    avx2_supported = check_avx2_support()
    pattern = (
        r"mpv-x86_64-v3-\d{8}-git-[a-f0-9]{7}\.7z"
        if avx2_supported
        else r"mpv-x86_64-\d{8}-git-[a-f0-9]{7}\.7z"
    )

    logging.debug(f"Searching for MPV using pattern: {pattern}")

    for name, link in direct_links.items():
        if re.match(pattern, name):
            logging.info(
                f"Found MPV download: {name} ({'with' if avx2_supported else 'without'} AVX2)"
            )
            return link

    return None


def _extract_with_7z(zip_tool: str, zip_path: str, dest_path: str) -> bool:
    """Extract archive using 7z tool."""
    try:
        return _run_command([zip_tool, "x", zip_path], cwd=dest_path)
    except Exception as e:
        logging.error(f"Failed to extract with 7z: {e}")
        return False


def _extract_with_tar(zip_path: str, dest_path: str) -> bool:
    """Extract archive using tar."""
    try:
        return _run_command(["tar", "-xf", zip_path], cwd=dest_path)
    except Exception as e:
        logging.error(f"Failed to extract with tar: {e}")
        return False


def download_mpv(
    dep_path: Optional[str] = None,
    appdata_path: Optional[str] = None,
    update: bool = False,
) -> bool:
    """
    Download and install MPV player.

    Args:
        dep_path: Installation directory
        appdata_path: AppData directory (Windows only)
        update: Whether to update existing installation

    Returns:
        True if installation successful
    """
    if update:
        logging.info("Updating MPV...")

    # macOS installation
    if sys.platform == "darwin":
        return _install_with_homebrew("mpv", update)

    # Linux installation
    if sys.platform == "linux":
        if MPV_PATH:
            return True
        return _install_with_package_manager("mpv")

    # Windows installation
    if sys.platform != "win32":
        return True

    appdata_path = appdata_path or DEFAULT_APPDATA_PATH
    dep_path = dep_path or os.path.join(appdata_path, "mpv")

    if update and os.path.exists(dep_path):
        _remove_directory_safe(dep_path)

    _ensure_directory(dep_path)

    executable_path = os.path.join(dep_path, "mpv.exe")
    if os.path.exists(executable_path) and not update:
        return True

    # Download MPV
    direct_links = get_github_release("shinchiro/mpv-winbuild-cmake")
    if not direct_links:
        logging.error("Failed to get MPV release information")
        return False

    direct_link = _get_mpv_download_link(direct_links)
    if not direct_link:
        logging.error("No suitable MPV download link found")
        return False

    zip_path = os.path.join(dep_path, "mpv.7z")
    zip_tool = os.path.join(appdata_path, "7z", "7zr.exe")

    _ensure_directory(os.path.dirname(zip_tool))

    # Download files
    if not download_file(direct_link, zip_path):
        return False

    if not _download_7z(zip_tool):
        return False

    # Extract
    logging.info("Extracting MPV...")
    if not _extract_with_7z(zip_tool, zip_path, dep_path):
        logging.error("Failed to extract MPV")
        return False

    # Add to PATH
    logging.debug(f"Adding MPV path to environment: {dep_path}")
    os.environ["PATH"] += os.pathsep + dep_path

    # Cleanup
    _remove_file_safe(zip_path)

    logging.info("MPV installation completed successfully")
    return True


def _get_syncplay_download_link(direct_links: Dict[str, str]) -> Optional[str]:
    """Get Syncplay download link."""
    for name, link in direct_links.items():
        if re.match(r"Syncplay_\d+\.\d+\.\d+_Portable\.zip", name):
            logging.info(f"Found Syncplay download: {name}")
            return link
    return None


def download_syncplay(
    dep_path: Optional[str] = None,
    appdata_path: Optional[str] = None,
    update: bool = False,
) -> bool:
    """
    Download and install Syncplay.

    Args:
        dep_path: Installation directory
        appdata_path: AppData directory (Windows only)
        update: Whether to update existing installation

    Returns:
        True if installation successful
    """
    if update:
        logging.info("Updating Syncplay...")

    # macOS installation
    if sys.platform == "darwin":
        return _install_with_homebrew("syncplay", update)

    # Linux installation
    if sys.platform == "linux":
        if SYNCPLAY_PATH:
            return True
        return _install_with_package_manager("syncplay")

    # Windows installation
    if sys.platform != "win32":
        return True

    appdata_path = appdata_path or DEFAULT_APPDATA_PATH
    dep_path = dep_path or os.path.join(appdata_path, "syncplay")

    if update and os.path.exists(dep_path):
        _remove_directory_safe(dep_path)

    _ensure_directory(dep_path)

    executable_path = os.path.join(dep_path, "SyncplayConsole.exe")
    if os.path.exists(executable_path) and not update:
        return True

    # Download Syncplay
    direct_links = get_github_release("Syncplay/syncplay")
    if not direct_links:
        logging.error("Failed to get Syncplay release information")
        return False

    direct_link = _get_syncplay_download_link(direct_links)
    if not direct_link:
        logging.error("No suitable Syncplay download link found")
        return False

    zip_path = os.path.join(dep_path, "syncplay.zip")

    # Download and extract
    if not download_file(direct_link, zip_path):
        return False

    logging.info("Extracting Syncplay...")
    if not _extract_with_tar(zip_path, dep_path):
        logging.error("Failed to extract Syncplay")
        return False

    # Cleanup
    _remove_file_safe(zip_path)

    logging.info("Syncplay installation completed successfully")
    return True


def _parse_season_episodes(soup: BeautifulSoup, season: int) -> int:
    """Parse episode count for a specific season."""
    episode_links = soup.find_all("a", href=True)
    unique_links = set(
        link["href"]
        for link in episode_links
        if f"staffel-{season}/episode-" in link["href"]
    )
    return len(unique_links)


def get_season_episode_count(slug: str) -> Dict[int, int]:
    """
    Get episode count for each season of an anime.

    Args:
        slug: Anime slug from URL

    Returns:
        Dictionary mapping season numbers to episode counts
    """
    try:
        base_url = f"{ANIWORLD_TO}/anime/stream/{slug}/"
        response = _make_request(base_url)
        soup = BeautifulSoup(response.content, "html.parser")

        season_meta = soup.find("meta", itemprop="numberOfSeasons")
        number_of_seasons = int(season_meta["content"]) if season_meta else 0

        episode_counts = {}
        for season in range(1, number_of_seasons + 1):
            season_url = f"{base_url}staffel-{season}"
            try:
                season_response = _make_request(season_url)
                season_soup = BeautifulSoup(season_response.content, "html.parser")
                episode_counts[season] = _parse_season_episodes(season_soup, season)
            except Exception as e:
                logging.warning(f"Failed to get episodes for season {season}: {e}")
                episode_counts[season] = 0

        return episode_counts

    except Exception as e:
        logging.error(f"Failed to get season episode count for {slug}: {e}")
        return {}


def get_movie_episode_count(slug: str) -> int:
    """
    Get movie count for an anime.

    Args:
        slug: Anime slug from URL

    Returns:
        Number of movies available
    """
    try:
        movie_page_url = f"{ANIWORLD_TO}/anime/stream/{slug}/filme"
        response = _make_request(movie_page_url)
        soup = BeautifulSoup(response.content, "html.parser")

        movie_indices = []
        movie_index = 1

        while True:
            expected_subpath = f"{slug}/filme/film-{movie_index}"
            matching_links = [
                link["href"]
                for link in soup.find_all("a", href=True)
                if expected_subpath in link["href"]
            ]

            if matching_links:
                movie_indices.append(movie_index)
                movie_index += 1
            else:
                break

        return max(movie_indices) if movie_indices else 0

    except Exception as e:
        logging.error(f"Failed to get movie count for {slug}: {e}")
        return 0


def _natural_sort_key(link_url: str) -> List:
    """Natural sort key for URLs."""
    return [
        int(text) if text.isdigit() else text for text in re.split(r"(\d+)", link_url)
    ]


def _process_base_url(
    base_url: str, arguments, slug_cache: Dict[str, Tuple[Dict[int, int], int]]
) -> Set[str]:
    """Process a single base URL to generate episode links."""
    unique_links = set()
    parts = base_url.split("/")

    if not (
        "anime" in parts
        and (
            "episode" not in base_url
            and "film-" not in base_url
            or arguments.keep_watching
        )
    ):
        unique_links.add(base_url)
        return unique_links

    try:
        series_slug_index = parts.index("stream") + 1
        series_slug = parts[series_slug_index]

        if series_slug in slug_cache:
            seasons_info, movies_info = slug_cache[series_slug]
        else:
            seasons_info = get_season_episode_count(slug=series_slug)
            movies_info = get_movie_episode_count(slug=series_slug)
            slug_cache[series_slug] = (seasons_info, movies_info)

    except (ValueError, IndexError) as e:
        logging.warning(f"Failed to parse URL {base_url}: {e}")
        unique_links.add(base_url)
        return unique_links

    # Remove trailing slash
    if base_url.endswith("/"):
        base_url = base_url[:-1]

    # Handle keep_watching mode
    if arguments.keep_watching:
        unique_links.update(_process_keep_watching(base_url, seasons_info, movies_info))
    else:
        unique_links.update(
            _process_full_series(base_url, parts, seasons_info, movies_info)
        )

    return unique_links


def _process_keep_watching(
    base_url: str, seasons_info: Dict[int, int], movies_info: int
) -> Set[str]:
    """Process keep_watching mode for URL generation."""
    unique_links = set()

    season_start = 1
    episode_start = 1
    movie_start = 1

    season_match = re.search(r"staffel-(\d+)", base_url)
    episode_match = re.search(r"episode-(\d+)", base_url)
    movie_match = re.search(r"film-(\d+)", base_url)

    if season_match:
        season_start = int(season_match.group(1))
    if episode_match:
        episode_start = int(episode_match.group(1))
    if movie_match:
        movie_start = int(movie_match.group(1))

    raw_url = "/".join(base_url.split("/")[:6])

    if "film" not in base_url:
        for season in range(season_start, len(seasons_info) + 1):
            season_url = f"{raw_url}/staffel-{season}/"
            for episode in range(episode_start, seasons_info[season] + 1):
                unique_links.add(f"{season_url}episode-{episode}")
            episode_start = 1
    else:
        for episode in range(movie_start, movies_info + 1):
            unique_links.add(f"{raw_url}/filme/film-{episode}")

    return unique_links


def _process_full_series(
    base_url: str, parts: List[str], seasons_info: Dict[int, int], movies_info: int
) -> Set[str]:
    """Process full series URL generation."""
    unique_links = set()

    # Handle different URL patterns
    if (
        "staffel" not in base_url
        and "episode" not in base_url
        and "film" not in base_url
    ):
        # Full series
        for season, episodes in seasons_info.items():
            season_url = f"{base_url}/staffel-{season}/"
            for episode in range(1, episodes + 1):
                unique_links.add(f"{season_url}episode-{episode}")
    elif "staffel" in base_url and "episode" not in base_url:
        # Specific season
        try:
            season = int(parts[-1].split("-")[-1])
            if season in seasons_info:
                for episode in range(1, seasons_info[season] + 1):
                    unique_links.add(f"{base_url}/episode-{episode}")
        except (ValueError, IndexError):
            unique_links.add(base_url)
    elif "filme" in base_url and "film-" not in base_url:
        # All movies
        for episode in range(1, movies_info + 1):
            unique_links.add(f"{base_url}/film-{episode}")
    else:
        # Specific episode/movie
        unique_links.add(base_url)

    return unique_links


def generate_links(urls: List[str], arguments) -> List[str]:
    """
    Generate episode/movie links from base URLs.

    Args:
        urls: List of base URLs
        arguments: Command line arguments

    Returns:
        Sorted list of episode/movie URLs
    """
    unique_links = set()
    slug_cache = {}

    for base_url in urls:
        try:
            links = _process_base_url(base_url, arguments, slug_cache)
            unique_links.update(links)
        except Exception as e:
            logging.error(f"Failed to process URL {base_url}: {e}")
            unique_links.add(base_url)

    return sorted(unique_links, key=_natural_sort_key)


def remove_anime4k() -> None:
    """Remove Anime4K files from MPV directory."""
    anime4k_paths = [
        os.path.join(MPV_DIRECTORY, "shaders"),
        os.path.join(MPV_DIRECTORY, "input.conf"),
        os.path.join(MPV_DIRECTORY, "mpv.conf"),
    ]

    for path in anime4k_paths:
        if os.path.isdir(path):
            logging.info(f"Removing directory: {path}")
            _remove_directory_safe(path)
        elif os.path.exists(path):
            logging.info(f"Removing file: {path}")
            _remove_file_safe(path)


def remove_mpv_scripts() -> None:
    """Remove MPV scripts from scripts directory."""
    scripts = ["aniskip.lua", "autoexit.lua", "autostart.lua"]
    scripts_dir = os.path.join(MPV_DIRECTORY, "scripts")

    for script in scripts:
        script_path = os.path.join(scripts_dir, script)
        if os.path.exists(script_path):
            logging.info(f"Removing script: {script_path}")
            _remove_file_safe(script_path)


def copy_file_if_different(source_path: str, destination_path: str) -> bool:
    """
    Copy file only if content differs or destination doesn't exist.

    Args:
        source_path: Source file path
        destination_path: Destination file path

    Returns:
        True if file was copied
    """
    try:
        if os.path.exists(destination_path):
            with open(source_path, "r", encoding="utf-8") as source_file:
                source_content = source_file.read()

            with open(destination_path, "r", encoding="utf-8") as destination_file:
                destination_content = destination_file.read()

            if source_content != destination_content:
                logging.debug(
                    f"Content differs, overwriting {os.path.basename(destination_path)}"
                )
                shutil.copy(source_path, destination_path)
                return True
            else:
                logging.debug(
                    f"{os.path.basename(destination_path)} already exists and is identical"
                )
                return False
        else:
            logging.debug(
                f"Copying {os.path.basename(source_path)} to {os.path.dirname(destination_path)}"
            )
            shutil.copy(source_path, destination_path)
            return True

    except Exception as e:
        logging.error(f"Failed to copy {source_path} to {destination_path}: {e}")
        return False


def _setup_script(script_name: str) -> bool:
    """Setup MPV script by copying from source to destination."""
    try:
        script_directory = Path(__file__).parent.parent
        mpv_scripts_directory = Path(MPV_SCRIPTS_DIRECTORY)

        # Ensure scripts directory exists
        mpv_scripts_directory.mkdir(parents=True, exist_ok=True)

        source_path = script_directory / "aniskip" / "scripts" / script_name
        destination_path = mpv_scripts_directory / script_name

        return copy_file_if_different(str(source_path), str(destination_path))

    except Exception as e:
        logging.error(f"Failed to setup {script_name}: {e}")
        return False


def setup_autostart() -> bool:
    """Setup autostart script for MPV."""
    logging.debug("Setting up autostart script")
    return _setup_script("autostart.lua")


def setup_autoexit() -> bool:
    """Setup autoexit script for MPV."""
    logging.debug("Setting up autoexit script")
    return _setup_script("autoexit.lua")


if __name__ == "__main__":
    print(f"AVX2 Support: {check_avx2_support()}")
