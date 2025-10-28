import os
import subprocess
from ..extractors.megakino_extractor import megakino_get_direct_link
from ..config import DEFAULT_MOVIE_DOWNLOAD_PATH
from ..models import Movie
from ..action.common import YTDLPManager, sanitize_filename

def download_movie(movie: Movie, progress_callback=None):
    direct_link = megakino_get_direct_link(movie.link)
    if not direct_link:
        raise ValueError("Could not get direct link for movie.")

    output_path = os.path.join(DEFAULT_MOVIE_DOWNLOAD_PATH, sanitize_filename(movie.title))
    output_file = os.path.join(output_path, f"{sanitize_filename(movie.title)}.mp4")

    ydl_opts = {
        'outtmpl': output_file,
        'progress_hooks': [progress_callback] if progress_callback else [],
    }

    with YTDLPManager(ydl_opts) as ydl:
        ydl.download([direct_link])
