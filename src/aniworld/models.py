import importlib
import json
import logging
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union, Any

import requests
import requests.models
from bs4 import BeautifulSoup

from aniworld.aniskip import get_mal_id_from_title
from aniworld.config import (
    DEFAULT_REQUEST_TIMEOUT,
    RANDOM_USER_AGENT,
    ANIWORLD_TO,
    SUPPORTED_PROVIDERS
)
from aniworld.parser import arguments
from aniworld.common import get_season_episode_count, get_movie_episode_count


# Language code mappings for consistent handling
LANGUAGE_CODES = {
    "German Dub": 1,
    "English Sub": 2,
    "German Sub": 3
}

LANGUAGE_NAMES = {
    1: "German Dub",
    2: "English Sub",
    3: "German Sub"
}


class Anime:
    """
    Represents an anime series with comprehensive data management and validation.

    This class provides a complete interface for anime data including metadata,
    episode management, and provider/language configuration with lazy loading
    and caching for optimal performance.

    Example:
        anime = Anime(
            episode_list=[
                Episode(
                    slug="loner-life-in-another-world",
                    season=1,
                    episode=1
                )
            ]
        )

    Required Attributes:
        episode_list (List[Episode]): A list of Episode objects for the anime.

    Attributes:
        title (str): The title of the anime.
        slug (str): A URL-friendly version of the title used for web requests.
        action (str): The default action to be performed ("Download", "Watch", "Syncplay").
        provider (str): The provider of the anime content.
        language (str): The language code for the anime.
        aniskip (bool): Whether to skip certain actions (default is False).
        output_directory (str): The directory where downloads are saved.
        episode_list (List[Episode]): A list of Episode objects for the anime.
        description_german (str): The German description of the anime.
        description_english (str): The English description of the anime.
        html (requests.models.Response): The HTML response object for the anime's webpage.
    """

    def __init__(
        self,
        title: Optional[str] = None,
        slug: Optional[str] = None,
        action: Optional[str] = None,
        provider: Optional[str] = None,
        language: Optional[str] = None,
        aniskip: bool = False,
        output_directory: Optional[str] = None,
        episode_list: Optional[List['Episode']] = None,
        description_german: Optional[str] = None,
        description_english: Optional[str] = None,
        html: Optional[requests.models.Response] = None
    ) -> None:
        """
        Initialize an Anime instance with comprehensive validation.

        Args:
            title: The anime title
            slug: URL-friendly anime identifier
            action: Action to perform (Watch/Download/Syncplay)
            provider: Streaming provider
            language: Language preference
            aniskip: Whether to skip intro/outro
            output_directory: Download directory
            episode_list: List of Episode objects
            description_german: German description
            description_english: English description
            html: Pre-fetched HTML response

        Raises:
            ValueError: If episode_list is empty or slug cannot be determined
            requests.RequestException: If fetching anime data fails
        """
        # Validate required parameters
        if not episode_list:
            raise ValueError(
                "Provide 'episode_list' with at least one episode.")

        # Extract slug from episode list if not provided
        self.slug = slug or self._extract_slug_from_episodes(episode_list)
        if not self.slug:
            raise ValueError(
                "Slug of Anime is None and cannot be determined from episodes.")

        # Initialize attributes with fallbacks to parser arguments
        self.action = action or getattr(arguments, 'action', 'Watch')
        self.provider = provider or getattr(arguments, 'provider', None)
        self.language = language or getattr(
            arguments, 'language', 'German Sub')
        self.aniskip = aniskip or getattr(arguments, 'aniskip', False)
        self.output_directory = output_directory or getattr(
            arguments, 'output_dir', '')
        self.episode_list = episode_list

        # Initialize HTML and title
        self._html_cache = html
        self._title_cache = title
        self._description_german_cache = description_german
        self._description_english_cache = description_english

    def _extract_slug_from_episodes(self, episode_list: List['Episode']) -> Optional[str]:
        """
        Extract slug from the first episode in the list.

        Args:
            episode_list: List of Episode objects

        Returns:
            Slug string or None if not found
        """
        try:
            return episode_list[0].slug if episode_list else None
        except (IndexError, AttributeError):
            return None

    @property
    def html(self) -> requests.models.Response:
        """
        Lazy-loaded HTML response for the anime page.

        Returns:
            HTML response object

        Raises:
            requests.RequestException: If HTTP request fails
        """
        if self._html_cache is None:
            try:
                self._html_cache = requests.get(
                    f"{ANIWORLD_TO}/anime/stream/{self.slug}",
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                    headers={'User-Agent': RANDOM_USER_AGENT}
                )
                self._html_cache.raise_for_status()
            except requests.RequestException as e:
                logging.error(
                    "Failed to fetch anime HTML for slug '%s': %s", self.slug, e)
                raise

        return self._html_cache

    @property
    def title(self) -> str:
        """
        Lazy-loaded anime title.

        Returns:
            Anime title string
        """
        if self._title_cache is None:
            try:
                self._title_cache = get_anime_title_from_html(self.html)
                if not self._title_cache:
                    self._title_cache = f"Unknown Anime ({self.slug})"
                    logging.warning(
                        "Could not extract title for anime slug: %s", self.slug)
            except Exception as e:
                logging.error("Error extracting anime title: %s", e)
                self._title_cache = f"Unknown Anime ({self.slug})"

        return self._title_cache

    @property
    def description_german(self) -> str:
        """
        Lazy-loaded German description.

        Returns:
            German description string
        """
        if self._description_german_cache is None:
            self._description_german_cache = self._fetch_description_german()

        return self._description_german_cache

    @property
    def description_english(self) -> str:
        """
        Lazy-loaded English description.

        Returns:
            English description string
        """
        if self._description_english_cache is None:
            self._description_english_cache = self._fetch_description_english()

        return self._description_english_cache

    def _fetch_description_german(self) -> str:
        """
        Fetch German description from anime HTML.

        Returns:
            German description or fallback message
        """
        try:
            soup = BeautifulSoup(self.html.content, 'html.parser')
            desc_div = soup.find('p', class_='seri_des')

            if desc_div:
                description = desc_div.get('data-full-description', '')
                if description:
                    return description

                # Fallback to div text content
                return desc_div.get_text(strip=True)

            return "Could not fetch German description."

        except Exception as e:
            logging.error("Error fetching German description: %s", e)
            return "Error fetching German description."

    def _fetch_description_english(self) -> str:
        """
        Fetch English description from MyAnimeList.

        Returns:
            English description or fallback message
        """
        try:
            anime_id = get_mal_id_from_title(self.title, 1)
            if not anime_id:
                return "Could not find MyAnimeList ID for English description."

            response = requests.get(
                f"https://myanimelist.net/anime/{anime_id}",
                timeout=DEFAULT_REQUEST_TIMEOUT,
                headers={'User-Agent': RANDOM_USER_AGENT}
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            desc_meta = soup.find('meta', property='og:description')

            if desc_meta and desc_meta.get('content'):
                return desc_meta['content']

            return "Could not fetch English description."

        except Exception as e:
            logging.error("Error fetching English description: %s", e)
            return "Error fetching English description."

    def validate_configuration(self) -> List[str]:
        """
        Validate anime configuration and return any issues.

        Returns:
            List of validation error messages
        """
        issues = []

        if not self.episode_list:
            issues.append("No episodes provided")

        if not self.slug:
            issues.append("No slug provided")

        if self.action not in ['Watch', 'Download', 'Syncplay']:
            issues.append(f"Invalid action: {self.action}")

        if self.language not in LANGUAGE_CODES:
            issues.append(f"Invalid language: {self.language}")

        return issues

    def __iter__(self) -> iter:
        """Iterate over episode list."""
        return iter(self.episode_list)

    def __getitem__(self, index: int) -> 'Episode':
        """Get episode by index."""
        return self.episode_list[index]

    def __len__(self) -> int:
        """Get number of episodes."""
        return len(self.episode_list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert anime to dictionary representation.

        Returns:
            Dictionary with anime data
        """
        return {
            "title": self.title,
            "slug": self.slug,
            "action": self.action,
            "provider": self.provider,
            "language": self.language,
            "aniskip": self.aniskip,
            "output_directory": str(self.output_directory),
            "episode_count": len(self.episode_list),
            "description_german": self._truncate_description(self.description_german),
            "description_english": self._truncate_description(self.description_english),
        }

    def _truncate_description(self, description: str, max_words: int = 10) -> str:
        """
        Truncate description to specified word count.

        Args:
            description: Description text
            max_words: Maximum number of words

        Returns:
            Truncated description with ellipsis if needed
        """
        if not description:
            return ""

        words = description.split()
        if len(words) <= max_words:
            return description

        return ' '.join(words[:max_words]) + ' [...]'

    def to_json(self) -> str:
        """
        Convert anime to JSON string representation.

        Returns:
            JSON string with anime data
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        """String representation of anime."""
        return f"Anime(title='{self.title}', episodes={len(self.episode_list)}, action='{self.action}')"

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Anime(title='{self.title}', slug='{self.slug}', "
                f"episodes={len(self.episode_list)}, action='{self.action}', "
                f"provider='{self.provider}', language='{self.language}')")


class Episode:
    """
    Represents an episode of an anime series with comprehensive data management.

    This class provides a complete interface for episode data including metadata,
    provider/language management, and streaming link generation with lazy loading
    and caching for optimal performance.

    Example:
        Episode(
            slug="loner-life-in-another-world",
            season=1,
            episode=1
        )

    Required Attributes:
        link (str) OR (slug (str) + season (int) + episode (int)):
        Either a direct link to the episode or components to construct it.

    Attributes:
        anime_title (str): The title of the anime the episode belongs to.
        title_german (str): The German title of the episode.
        title_english (str): The English title of the episode.
        season (int): The season number (0 for movies).
        episode (int): The episode number within the season.
        slug (str): URL-friendly anime identifier.
        link (str): The direct link to the episode page.
        mal_id (int): The MyAnimeList ID for the episode.
        redirect_link (str): The redirect link for streaming.
        embeded_link (str): The embedded streaming link.
        direct_link (str): The direct streaming link.
        provider (Dict[str, Dict[int, str]]): Available providers and their links.
        provider_name (List[str]): List of provider names.
        language (List[int]): List of available language codes.
        language_name (List[str]): List of available language names.
        season_episode_count (Dict[int, int]): Season to episode count mapping.
        movie_episode_count (int): Number of movie episodes.
        html (requests.models.Response): HTML response object.
        _selected_provider (str): Currently selected provider.
        _selected_language (str): Currently selected language.
    """

    def __init__(
        self,
        anime_title: Optional[str] = None,
        title_german: Optional[str] = None,
        title_english: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        slug: Optional[str] = None,
        link: Optional[str] = None,
        mal_id: Optional[int] = None,
        redirect_link: Optional[str] = None,
        embeded_link: Optional[str] = None,
        direct_link: Optional[str] = None,
        provider: Optional[Dict[str, Dict[int, str]]] = None,
        provider_name: Optional[List[str]] = None,
        language: Optional[List[int]] = None,
        language_name: Optional[List[str]] = None,
        season_episode_count: Optional[Dict[int, int]] = None,
        has_movies: bool = False,
        movie_episode_count: Optional[int] = None,
        html: Optional[requests.models.Response] = None,
        _selected_provider: Optional[str] = None,
        _selected_language: Optional[str] = None
    ) -> None:
        """
        Initialize an Episode instance with comprehensive validation.

        Args:
            anime_title: Anime title
            title_german: German episode title
            title_english: English episode title
            season: Season number (0 for movies)
            episode: Episode number
            slug: Anime slug identifier
            link: Direct episode link
            mal_id: MyAnimeList ID
            redirect_link: Redirect streaming link
            embeded_link: Embedded streaming link
            direct_link: Direct streaming link
            provider: Available providers dictionary
            provider_name: List of provider names
            language: Available language codes
            language_name: Available language names
            season_episode_count: Season episode counts
            has_movies: Whether anime has movies
            movie_episode_count: Number of movies
            html: Pre-fetched HTML response
            _selected_provider: Selected provider
            _selected_language: Selected language

        Raises:
            ValueError: If neither link nor (slug + season + episode) provided
        """
        # Validate required parameters
        if not link and (not slug or season is None or episode is None):
            raise ValueError(
                "Provide either 'link' or 'slug' with 'season' and 'episode'."
            )

        # Initialize core attributes
        self.anime_title = anime_title
        self.title_german = title_german
        self.title_english = title_english
        self.season = season
        self.episode = episode
        self.slug = slug
        self.link = link
        self.mal_id = mal_id

        # Initialize streaming attributes
        self.redirect_link = redirect_link
        self.embeded_link = embeded_link
        self.direct_link = direct_link

        # Initialize provider and language data
        self.provider = provider or {}
        self.provider_name = provider_name or []
        self.language = language or []
        self.language_name = language_name or []

        # Initialize metadata
        self.season_episode_count = season_episode_count or {}
        self.has_movies = has_movies
        self.movie_episode_count = movie_episode_count or 0

        # Initialize selected options with fallbacks
        self._selected_provider = (_selected_provider or
                                   getattr(arguments, 'provider', None))
        self._selected_language = (_selected_language or
                                   getattr(arguments, 'language', 'German Sub'))

        # Cache for HTML and other expensive operations
        self._html_cache = html
        self._provider_cache = None
        self._language_cache = None

        # Auto-populate details
        self.auto_fill_details()

    @property
    def html(self) -> requests.models.Response:
        """
        Lazy-loaded HTML response for the episode page.

        Returns:
            HTML response object

        Raises:
            requests.RequestException: If HTTP request fails
        """
        if self._html_cache is None:
            if not self.link:
                raise ValueError("Cannot fetch HTML without episode link")

            try:
                self._html_cache = requests.get(
                    self.link,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                    headers={'User-Agent': RANDOM_USER_AGENT}
                )
                self._html_cache.raise_for_status()
            except requests.RequestException as e:
                logging.error(
                    "Failed to fetch episode HTML for link '%s': %s", self.link, e)
                raise

        return self._html_cache

    def _get_episode_titles_from_html(self) -> Tuple[str, str]:
        """
        Extract episode titles from HTML.

        Returns:
            Tuple of (german_title, english_title)
        """
        try:
            episode_soup = BeautifulSoup(self.html.content, 'html.parser')

            german_title_div = episode_soup.find(
                'span', class_='episodeGermanTitle')
            english_title_div = episode_soup.find(
                'small', class_='episodeEnglishTitle')

            german_title = german_title_div.get_text(
                strip=True) if german_title_div else ""
            english_title = english_title_div.get_text(
                strip=True) if english_title_div else ""

            return german_title, english_title

        except Exception as e:
            logging.error("Error extracting episode titles: %s", e)
            return "", ""

    def _extract_season_from_link(self) -> int:
        """
        Extract season number from episode link.

        Returns:
            Season number (0 for movies)

        Raises:
            ValueError: If season cannot be extracted
        """
        if not self.link:
            raise ValueError("No link provided to extract season from")

        # Check if it's a movie
        if "/filme/" in self.link:
            return 0

        # Extract season from link pattern like /staffel-2/
        try:
            season_part = self.link.split("/")[-2]  # e.g., "staffel-2"
            numbers = re.findall(r'\d+', season_part)

            if numbers:
                return int(numbers[-1])

            raise ValueError(
                f"No valid season number found in link: {self.link}")

        except (IndexError, ValueError) as e:
            raise ValueError(
                f"Failed to extract season from link '{self.link}': {e}") from e

    def _extract_episode_from_link(self) -> int:
        """
        Extract episode number from episode link.

        Returns:
            Episode number

        Raises:
            ValueError: If episode cannot be extracted
        """
        if not self.link:
            raise ValueError("No link provided to extract episode from")

        try:
            # Remove trailing slash if present
            link = self.link.rstrip("/")

            # Extract episode from link pattern like /episode-2 or /film-1
            episode_part = link.split("/")[-1]  # e.g., "episode-2" or "film-1"
            numbers = re.findall(r'\d+', episode_part)

            if numbers:
                return int(numbers[-1])

            raise ValueError(
                f"No valid episode number found in link: {self.link}")

        except (IndexError, ValueError) as e:
            raise ValueError(
                f"Failed to extract episode from link '{self.link}': {e}") from e

    @lru_cache(maxsize=32)
    def _get_available_languages_from_html(self) -> List[int]:
        """
        Extract available language codes from HTML with caching.

        Language Codes:
            1: German Dub
            2: English Sub
            3: German Sub

        Returns:
            List of available language codes
        """
        try:
            episode_soup = BeautifulSoup(self.html.content, 'html.parser')
            change_language_box = episode_soup.find(
                'div', class_='changeLanguageBox')

            if not change_language_box:
                logging.warning(
                    "No language selection box found for episode: %s", self.link)
                return []

            language_codes = []
            img_tags = change_language_box.find_all('img')

            for img in img_tags:
                lang_key = img.get('data-lang-key')
                if lang_key and lang_key.isdigit():
                    language_codes.append(int(lang_key))

            return sorted(language_codes)

        except Exception as e:
            logging.error("Error extracting language codes: %s", e)
            return []

    @lru_cache(maxsize=32)
    def _get_providers_from_html(self) -> Dict[str, Dict[int, str]]:
        """
        Extract streaming providers from HTML with caching.

        Returns:
            Dictionary mapping provider names to language-URL mappings

        Example:
            {
                'VOE': {1: 'https://aniworld.to/redirect/1766412',
                        2: 'https://aniworld.to/redirect/1766405'},
                'Doodstream': {1: 'https://aniworld.to/redirect/1987922',
                               2: 'https://aniworld.to/redirect/2700342'}
            }

        Raises:
            ValueError: If no providers found
        """
        try:
            soup = BeautifulSoup(self.html.content, 'html.parser')
            providers = {}

            episode_links = soup.find_all(
                'li', class_=lambda x: x and x.startswith('episodeLink')
            )

            if not episode_links:
                raise ValueError(
                    f"No streams available for episode: {self.link}\n"
                    "Try again later or check in the community chat."
                )

            for link in episode_links:
                provider_data = self._extract_provider_data(link)
                if provider_data:
                    provider_name, lang_key, redirect_url = provider_data

                    if provider_name not in providers:
                        providers[provider_name] = {}

                    providers[provider_name][lang_key] = redirect_url

            if not providers:
                raise ValueError(
                    f"Could not extract providers from {self.link}")

            logging.debug("Available providers for \"%s\":\n%s",
                          self.anime_title, json.dumps(providers, indent=2))

            return providers

        except Exception as e:
            logging.error("Error extracting providers: %s", e)
            raise

    def _extract_provider_data(self, link_element) -> Optional[Tuple[str, int, str]]:
        """
        Extract provider data from HTML element.

        Args:
            link_element: BeautifulSoup element containing provider data

        Returns:
            Tuple of (provider_name, lang_key, redirect_url) or None
        """
        try:
            # Extract provider name
            provider_name_tag = link_element.find('h4')
            provider_name = provider_name_tag.get_text(
                strip=True) if provider_name_tag else None

            # Extract redirect link
            redirect_link_tag = link_element.find('a', class_='watchEpisode')
            redirect_path = redirect_link_tag.get(
                'href') if redirect_link_tag else None

            # Extract language key
            lang_key_str = link_element.get('data-lang-key')
            lang_key = int(
                lang_key_str) if lang_key_str and lang_key_str.isdigit() else None

            # Validate all required data is present
            if provider_name and redirect_path and lang_key:
                redirect_url = f"{ANIWORLD_TO}{redirect_path}"
                return provider_name, lang_key, redirect_url

            return None

        except (ValueError, AttributeError) as e:
            logging.debug(
                "Failed to extract provider data from element: %s", e)
            return None

    def _get_language_key_from_name(self, language_name: str) -> int:
        """
        Convert language name to language key.

        Args:
            language_name: Language name (e.g., "German Dub")

        Returns:
            Language key integer

        Raises:
            ValueError: If language name is invalid
        """
        language_key = LANGUAGE_CODES.get(language_name)

        if language_key is None:
            valid_languages = list(LANGUAGE_CODES.keys())
            raise ValueError(
                f"Invalid language: {language_name}. Valid options: {valid_languages}")

        return language_key

    def _get_language_names_from_keys(self, language_keys: List[int]) -> List[str]:
        """
        Convert language keys to language names.

        Args:
            language_keys: List of language key integers

        Returns:
            List of language names

        Raises:
            ValueError: If any language key is invalid
        """
        language_names = []

        for key in language_keys:
            name = LANGUAGE_NAMES.get(key)
            if name is None:
                raise ValueError(f"Invalid language key: {key}")
            language_names.append(name)

        return language_names

    def _get_direct_link_from_provider(self) -> str:
        """
        Get direct streaming link from the selected provider.

        Returns:
            Direct streaming link

        Raises:
            ValueError: If provider is not supported or extraction fails
        """
        provider = self._selected_provider

        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Provider '{provider}' is currently not supported. "
                             f"Supported providers: {SUPPORTED_PROVIDERS}")

        if not self.embeded_link:
            raise ValueError(
                "No embedded link available for direct link extraction")

        try:
            module = importlib.import_module("aniworld.extractors")
            func_name = f"get_direct_link_from_{provider.lower()}"

            if not hasattr(module, func_name):
                raise ValueError(f"Extractor function '{func_name}' not found")

            func = getattr(module, func_name)

            # Prepare kwargs for the extractor function
            kwargs = {f"embeded_{provider.lower()}_link": self.embeded_link}

            # Special case for Luluvdo which needs arguments
            if provider == "Luluvdo":
                kwargs["arguments"] = arguments

            direct_link = func(**kwargs)

            if not direct_link:
                raise ValueError(
                    f"Provider '{provider}' returned empty direct link")

            return direct_link

        except Exception as e:
            logging.error(
                "Error getting direct link from provider '%s': %s", provider, e)
            raise ValueError(
                f"Failed to get direct link from provider '{provider}': {e}") from e

    def get_redirect_link(self) -> Optional[str]:
        """
        Get redirect link for the selected provider and language.

        Returns:
            Redirect link or None if not available
        """
        try:
            lang_key = self._get_language_key_from_name(
                self._selected_language)

            # Check if selected provider and language combination exists
            if (self._selected_provider in self.provider and
                    lang_key in self.provider[self._selected_provider]):
                self.redirect_link = self.provider[self._selected_provider][lang_key]
                return self.redirect_link

            # Fallback: find any provider with the selected language
            for provider_name, lang_dict in self.provider.items():
                if lang_key in lang_dict:
                    logging.info("Switching provider from '%s' to '%s' for language '%s'",
                                 self._selected_provider, provider_name, self._selected_language)
                    self._selected_provider = provider_name
                    self.redirect_link = lang_dict[lang_key]
                    return self.redirect_link

            # No provider found with selected language
            available_langs = set()
            for lang_dict in self.provider.values():
                available_langs.update(lang_dict.keys())

            available_lang_names = [LANGUAGE_NAMES.get(key, f"Unknown({key})")
                                    for key in available_langs]

            logging.warning("No provider found for language '%s'. Available languages: %s",
                            self._selected_language, available_lang_names)

            self.redirect_link = None
            return None

        except Exception as e:
            logging.error("Error getting redirect link: %s", e)
            self.redirect_link = None
            return None

    def get_embeded_link(self) -> Optional[str]:
        """
        Get embedded streaming link by following the redirect.

        Returns:
            Embedded link or None if unavailable
        """
        if not self.redirect_link:
            self.get_redirect_link()

        if not self.redirect_link:
            logging.warning(
                "No redirect link available for embedded link extraction")
            return None

        try:
            response = requests.get(
                self.redirect_link,
                timeout=DEFAULT_REQUEST_TIMEOUT,
                headers={'User-Agent': RANDOM_USER_AGENT},
                allow_redirects=True
            )
            response.raise_for_status()

            self.embeded_link = response.url
            return self.embeded_link

        except requests.RequestException as e:
            logging.error(
                "Error getting embedded link from '%s': %s", self.redirect_link, e)
            self.embeded_link = None
            return None

    def get_direct_link(self, provider: Optional[str] = None,
                        language: Optional[str] = None) -> Optional[str]:
        """
        Get the direct streaming link for the episode.

        Args:
            provider: Provider name to use (overrides selected provider)
            language: Language to use (overrides selected language)

        Returns:
            Direct streaming link or None if unavailable

        Example:
            episode.get_direct_link("VOE", "German Sub")
        """
        # Update selected options if provided
        if provider:
            self._selected_provider = provider

        if language:
            self._selected_language = language

        # Validate selected provider
        if self._selected_provider not in SUPPORTED_PROVIDERS:
            logging.error("Provider '%s' is not supported",
                          self._selected_provider)
            return None

        try:
            # Get embedded link if not already available
            if not self.embeded_link:
                if not self.get_embeded_link():
                    logging.error("Failed to get embedded link")
                    return None

            # Get direct link from provider
            self.direct_link = self._get_direct_link_from_provider()
            return self.direct_link

        except Exception as e:
            logging.error("Error getting direct link: %s", e)
            self.direct_link = None
            return None

    def auto_fill_details(self) -> None:
        """
        Automatically fill episode details from available information.

        This method constructs missing information like links, extracts metadata
        from HTML, and populates provider/language information.
        """
        try:
            # Construct link if missing but have components
            if not self.link and self.slug and self.season is not None and self.episode is not None:
                if self.season == 0:  # Movie
                    self.link = f"{ANIWORLD_TO}/anime/stream/{self.slug}/filme/film-{self.episode}"
                else:  # Regular episode
                    self.link = (f"{ANIWORLD_TO}/anime/stream/{self.slug}/"
                                 f"staffel-{self.season}/episode-{self.episode}")

            # Extract components from link if missing
            if self.link:
                if not self.slug:
                    try:
                        self.slug = self.link.split("/")[-3]
                    except IndexError:
                        logging.warning(
                            "Could not extract slug from link: %s", self.link)

                if self.season is None:
                    try:
                        self.season = self._extract_season_from_link()
                    except ValueError as e:
                        logging.warning("Could not extract season: %s", e)

                if self.episode is None:
                    try:
                        self.episode = self._extract_episode_from_link()
                    except ValueError as e:
                        logging.warning("Could not extract episode: %s", e)

            # Fetch and populate metadata if link is available
            if self.link:
                try:
                    # Get anime title if missing
                    if not self.anime_title:
                        self.anime_title = get_anime_title_from_html(self.html)

                    # Get episode titles if missing
                    if not self.title_german and not self.title_english:
                        self.title_german, self.title_english = self._get_episode_titles_from_html()

                    # Get available languages
                    if not self.language:
                        self.language = self._get_available_languages_from_html()

                    # Get language names
                    if not self.language_name and self.language:
                        self.language_name = self._get_language_names_from_keys(
                            self.language)

                    # Get providers
                    if not self.provider:
                        self.provider = self._get_providers_from_html()

                    # Get provider names
                    if not self.provider_name and self.provider:
                        self.provider_name = list(self.provider.keys())

                    # Get season/episode counts if missing
                    if not self.season_episode_count and self.slug:
                        self.season_episode_count = get_season_episode_count(
                            self.slug)

                    if self.movie_episode_count is None and self.slug:
                        self.movie_episode_count = get_movie_episode_count(
                            self.slug)

                    # Clean up season episode count if movies exist
                    if (self.movie_episode_count and self.movie_episode_count > 0 and
                            self.season_episode_count):
                        # Remove season 0 if it exists and equals movie count
                        last_season = max(self.season_episode_count.keys(
                        )) if self.season_episode_count else None
                        if (last_season is not None and
                                self.season_episode_count.get(last_season) == 0):
                            del self.season_episode_count[last_season]

                except Exception as e:
                    logging.error("Error auto-filling episode details: %s", e)

        except Exception as e:
            logging.error("Critical error in auto_fill_details: %s", e)

    def validate_configuration(self) -> List[str]:
        """
        Validate episode configuration and return any issues.

        Returns:
            List of validation error messages
        """
        issues = []

        if not self.link and (not self.slug or self.season is None or self.episode is None):
            issues.append(
                "Either 'link' or 'slug + season + episode' must be provided")

        if self._selected_language not in LANGUAGE_CODES:
            issues.append(
                f"Invalid selected language: {self._selected_language}")

        if self._selected_provider and self._selected_provider not in SUPPORTED_PROVIDERS:
            issues.append(f"Unsupported provider: {self._selected_provider}")

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert episode to dictionary representation.

        Returns:
            Dictionary with episode data
        """
        return {
            "anime_title": self.anime_title,
            "title_german": self.title_german,
            "title_english": self.title_english,
            "season": self.season,
            "episode": self.episode,
            "slug": self.slug,
            "link": self.link,
            "mal_id": self.mal_id,
            "redirect_link": self.redirect_link,
            "embeded_link": self.embeded_link,
            "direct_link": self.direct_link,
            "provider_count": len(self.provider) if self.provider else 0,
            "provider_names": self.provider_name,
            "language_codes": self.language,
            "language_names": self.language_name,
            "selected_provider": self._selected_provider,
            "selected_language": self._selected_language,
            "season_episode_count": self.season_episode_count,
            "movie_episode_count": self.movie_episode_count,
        }

    def to_json(self) -> str:
        """
        Convert episode to JSON string representation.

        Returns:
            JSON string with episode data
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        """String representation of episode."""
        return (f"Episode(anime='{self.anime_title}', S{self.season:02d}E{self.episode:02d}, "
                f"provider='{self._selected_provider}', language='{self._selected_language}')")

    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"Episode(anime_title='{self.anime_title}', season={self.season}, "
                f"episode={self.episode}, slug='{self.slug}', "
                f"selected_provider='{self._selected_provider}', "
                f"selected_language='{self._selected_language}')")


def get_anime_title_from_html(html: requests.models.Response):
    soup = BeautifulSoup(html.content, 'html.parser')
    title_div = soup.find('div', class_='series-title')

    if title_div:
        return title_div.find('h1').find('span').text

    return ""


if __name__ == "__main__":
    pass
