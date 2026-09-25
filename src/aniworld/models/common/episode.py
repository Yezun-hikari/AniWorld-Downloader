import os
from pathlib import Path
from ...config import NAMING_TEMPLATE

class BaseEpisode:
    """Base class for episode models."""

    @property
    def _base_folder(self):
        # We use getattr with the mangled name for the subclass
        cache_key = f"_{self.__class__.__name__}__base_folder"
        if getattr(self, cache_key, None) is None:
            naming_template = os.getenv("ANIWORLD_NAMING_TEMPLATE", NAMING_TEMPLATE)
            parts = naming_template.split("/")
            if len(parts) <= 1:
                setattr(self, cache_key, Path(self.selected_path))
            else:
                folder_str = parts[0].format(
                    title=self.series.title_cleaned,
                    year=self.series.release_year,
                    imdbid=self.series.imdb,
                    season=f"{self.season.season_number:02d}",
                    episode=f"{self.episode_number:03d}",
                    language=self.selected_language,
                    resolution=getattr(self, "_resolution", "unknown"),
                )
                setattr(self, cache_key, Path(self.selected_path) / folder_str)
        return getattr(self, cache_key)

    @property
    def _folder_path(self):
        cache_key = f"_{self.__class__.__name__}__folder_path"
        if getattr(self, cache_key, None) is None:
            naming_template = os.getenv("ANIWORLD_NAMING_TEMPLATE", NAMING_TEMPLATE)
            parts = naming_template.split("/")
            if len(parts) <= 2:
                # No season subfolder (template is "file" or "folder/file")
                setattr(self, cache_key, self._base_folder)
            else:
                folder_str = parts[1].format(
                    title=self.series.title_cleaned,
                    year=self.series.release_year,
                    imdbid=self.series.imdb,
                    season=f"{self.season.season_number:02d}",
                    episode=f"{self.episode_number:03d}",
                    language=self.selected_language,
                    resolution=getattr(self, "_resolution", "unknown"),
                )
                setattr(self, cache_key, self._base_folder / folder_str)
        return getattr(self, cache_key)

    @property
    def _file_name(self):
        cache_key = f"_{self.__class__.__name__}__file_name"
        if getattr(self, cache_key, None) is None:
            naming_template = os.getenv("ANIWORLD_NAMING_TEMPLATE", NAMING_TEMPLATE)
            try:
                file_template = naming_template.split("/")[-1]
            except IndexError:
                file_template = f"{self.series.title_cleaned} S{self.season.season_number:02d}E{self.episode_number:03d}.mkv"

            # Remove extension
            if "." in file_template:
                file_template = ".".join(file_template.split(".")[:-1])

            # Replace %style% with {style} for compatibility
            file_template = file_template.replace("%title%", "{title}")
            file_template = file_template.replace("%year%", "{year}")
            file_template = file_template.replace("%imdbid%", "{imdbid}")
            file_template = file_template.replace("%season%", "{season}")
            file_template = file_template.replace("%episode%", "{episode}")
            file_template = file_template.replace("%language%", "{language}")
            file_template = file_template.replace("%resolution%", "{resolution}")

            file_name = file_template.format(
                title=self.series.title_cleaned,
                year=self.series.release_year,
                imdbid=self.series.imdb,
                season=f"{self.season.season_number:02d}",
                episode=f"{self.episode_number:03d}",
                language=self.selected_language,
                resolution=getattr(self, "_resolution", "unknown"),
            )
            setattr(self, cache_key, file_name)
        return getattr(self, cache_key)

    @property
    def _file_extension(self):
        cache_key = f"_{self.__class__.__name__}__file_extension"
        if getattr(self, cache_key, None) is None:
            naming_template = os.getenv("ANIWORLD_NAMING_TEMPLATE", NAMING_TEMPLATE)
            try:
                file_part = naming_template.split("/")[-1]
                if "." in file_part:
                    ext = file_part.rsplit(".", 1)[-1]
                    file_ext = ext if ext else "mkv"
                else:
                    file_ext = "mkv"
            except IndexError:
                file_ext = "mkv"
            setattr(self, cache_key, file_ext)
        return getattr(self, cache_key)

    @property
    def _episode_path(self):
        cache_key = f"_{self.__class__.__name__}__episode_path"
        if getattr(self, cache_key, None) is None:
            ep_path = self._folder_path / f"{self._file_name}.{self._file_extension}"
            setattr(self, cache_key, ep_path)
        return getattr(self, cache_key)
