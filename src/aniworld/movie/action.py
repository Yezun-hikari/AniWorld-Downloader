import os
import subprocess
from ..extractors.megakino_extractor import megakino_get_direct_link
from ..config import DEFAULT_MOVIE_DOWNLOAD_PATH
from ..models import Movie

def download_movie(movie: Movie):
    direct_link = megakino_get_direct_link(movie.link)
    if direct_link:
        output_file = os.path.join(DEFAULT_MOVIE_DOWNLOAD_PATH, f"{movie.title}.mp4")
        command = [
            "yt-dlp",
            "--fragment-retries", "infinite",
            "--concurrent-fragments", "4",
            "-o", output_file,
            "--quiet",
            "--no-warnings",
            direct_link,
            "--progress"
        ]
        subprocess.run(command)
