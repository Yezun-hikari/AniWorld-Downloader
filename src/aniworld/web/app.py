"""
Flask web application for AniWorld Downloader
"""

import logging
import os
import time
from datetime import datetime
from flask import Flask, render_template, jsonify

from .. import config


class WebApp:
    """Flask web application wrapper for AniWorld Downloader"""

    def __init__(self, host='127.0.0.1', port=5000, debug=False, arguments=None):
        """
        Initialize the Flask web application.

        Args:
            host: Host to bind to (default: 127.0.0.1)
            port: Port to bind to (default: 5000)
            debug: Enable Flask debug mode (default: False)
            arguments: Command line arguments object
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.arguments = arguments
        self.start_time = time.time()

        # Create Flask app
        self.app = self._create_app()

        # Setup routes
        self._setup_routes()

        # Download progress tracking
        self.download_progress = {
            'active': False,
            'anime_title': '',
            'total_episodes': 0,
            'completed_episodes': 0,
            'current_episode': '',
            'start_time': None
        }

    def _create_app(self) -> Flask:
        """Create and configure Flask application."""
        # Get the web module directory
        web_dir = os.path.dirname(os.path.abspath(__file__))

        app = Flask(
            __name__,
            template_folder=os.path.join(web_dir, 'templates'),
            static_folder=os.path.join(web_dir, 'static')
        )

        # Configure Flask
        app.config['SECRET_KEY'] = os.urandom(24)
        app.config['JSON_SORT_KEYS'] = False

        return app

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/')
        def index():
            """Main page route."""
            return render_template('index.html')

        @self.app.route('/api/test')
        def api_test():
            """API test endpoint."""
            return jsonify({
                'status': 'success',
                'message': 'Connection test successful',
                'timestamp': datetime.now().isoformat(),
                'version': config.VERSION
            })

        @self.app.route('/api/info')
        def api_info():
            """API info endpoint."""
            uptime_seconds = int(time.time() - self.start_time)
            uptime_str = self._format_uptime(uptime_seconds)

            # Convert latest_version to string if it's a Version object
            latest_version = getattr(config, 'LATEST_VERSION', None)
            if latest_version is not None:
                latest_version = str(latest_version)

            return jsonify({
                'version': config.VERSION,
                'status': 'running',
                'uptime': uptime_str,
                'latest_version': latest_version,
                'is_newest': getattr(config, 'IS_NEWEST_VERSION', True),
                'supported_providers': list(config.SUPPORTED_PROVIDERS),
                'platform': config.PLATFORM_SYSTEM
            })

        @self.app.route('/health')
        def health():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/api/search', methods=['POST'])
        def api_search():
            """Search for anime endpoint."""
            try:
                from flask import request
                data = request.get_json()
                if not data or 'query' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Query parameter is required'
                    }), 400

                query = data['query'].strip()
                if not query:
                    return jsonify({
                        'success': False,
                        'error': 'Query cannot be empty'
                    }), 400

                # Get site parameter (default to both)
                site = data.get('site', 'both')

                # Create wrapper function for search with dual-site support
                def search_anime_wrapper(keyword, site='both'):
                    """Wrapper function for anime search with multi-site support"""
                    from ..search import fetch_anime_list
                    from .. import config
                    from urllib.parse import quote

                    if site == 'both':
                        # Search both sites using existing fetch_anime_list function
                        aniworld_url = f"{config.ANIWORLD_TO}/ajax/seriesSearch?keyword={quote(keyword)}"
                        sto_url = f"{config.S_TO}/ajax/seriesSearch?keyword={quote(keyword)}"

                        # Fetch from both sites
                        aniworld_results = []
                        sto_results = []

                        try:
                            aniworld_results = fetch_anime_list(aniworld_url)
                        except Exception as e:
                            logging.warning(f"Failed to fetch from aniworld: {e}")

                        try:
                            sto_results = fetch_anime_list(sto_url)
                        except Exception as e:
                            logging.warning(f"Failed to fetch from s.to: {e}")

                        # Combine and deduplicate results
                        all_results = []
                        seen_slugs = set()

                        # Add aniworld results first
                        for anime in aniworld_results:
                            slug = anime.get('link', '')
                            if slug and slug not in seen_slugs:
                                anime['site'] = 'aniworld.to'
                                anime['base_url'] = config.ANIWORLD_TO
                                anime['stream_path'] = 'anime/stream'
                                all_results.append(anime)
                                seen_slugs.add(slug)

                        # Add s.to results, but skip duplicates
                        for anime in sto_results:
                            slug = anime.get('link', '')
                            if slug and slug not in seen_slugs:
                                anime['site'] = 's.to'
                                anime['base_url'] = config.S_TO
                                anime['stream_path'] = 'serie/stream'
                                all_results.append(anime)
                                seen_slugs.add(slug)

                        return all_results

                    elif site == 's.to':
                        # Single site search - s.to
                        search_url = f"{config.S_TO}/ajax/seriesSearch?keyword={quote(keyword)}"
                        try:
                            results = fetch_anime_list(search_url)
                            for anime in results:
                                anime['site'] = 's.to'
                                anime['base_url'] = config.S_TO
                                anime['stream_path'] = 'serie/stream'
                            return results
                        except Exception as e:
                            logging.error(f"s.to search failed: {e}")
                            return []

                    else:
                        # Single site search - aniworld.to (default)
                        from ..search import search_anime
                        try:
                            results = search_anime(keyword=keyword, only_return=True)
                            for anime in results:
                                anime['site'] = 'aniworld.to'
                                anime['base_url'] = config.ANIWORLD_TO
                                anime['stream_path'] = 'anime/stream'
                            return results
                        except Exception as e:
                            logging.error(f"aniworld.to search failed: {e}")
                            return []

                # Use wrapper function
                results = search_anime_wrapper(query, site)

                # Process results - simplified without episode fetching
                processed_results = []
                for anime in results[:50]:  # Limit to 50 results
                    # Get the link and construct full URL if needed
                    link = anime.get('link', '')
                    anime_site = anime.get('site', 'aniworld')
                    anime_base_url = anime.get('base_url', config.ANIWORLD_TO)
                    anime_stream_path = anime.get('stream_path', 'anime/stream')

                    if link and not link.startswith('http'):
                        # If it's just a slug, construct the full URL using the anime's specific site info
                        full_url = f"{anime_base_url}/{anime_stream_path}/{link}"
                    else:
                        full_url = link

                    # Use the same field names as CLI search
                    name = anime.get('name', 'Unknown Name')
                    year = anime.get('productionYear', 'Unknown Year')

                    # Create title like CLI does, but avoid double parentheses
                    if year and year != 'Unknown Year' and str(year) not in name:
                        title = f"{name} ({year})"
                    else:
                        title = name

                    processed_anime = {
                        'title': title,
                        'url': full_url,
                        'description': anime.get('description', ''),
                        'slug': link,
                        'name': name,
                        'year': year,
                        'site': anime_site,
                        'cover': anime.get('cover', '')
                    }

                    processed_results.append(processed_anime)

                return jsonify({
                    'success': True,
                    'results': processed_results,
                    'count': len(processed_results)
                })

            except Exception as err:
                logging.error(f"Search error: {err}")
                return jsonify({
                    'success': False,
                    'error': f'Search failed: {str(err)}'
                }), 500

        @self.app.route('/api/download', methods=['POST'])
        def api_download():
            """Start download endpoint."""
            try:
                from flask import request
                data = request.get_json()

                # Check for both single episode (legacy) and multiple episodes (new)
                episode_urls = data.get('episode_urls', [])
                single_episode_url = data.get('episode_url')

                if single_episode_url:
                    episode_urls = [single_episode_url]

                if not episode_urls:
                    return jsonify({
                        'success': False,
                        'error': 'Episode URL(s) required'
                    }), 400

                language = data.get('language', 'German Sub')
                provider = data.get('provider', 'VOE')

                # DEBUG: Log received parameters
                logging.warning(f"WEB API RECEIVED - Language: '{language}', Provider: '{provider}'")
                logging.warning(f"WEB API RECEIVED - Request data: {data}")

                # Import necessary modules - use existing high-level functions
                from ..execute import execute
                from ..entry import _group_episodes_by_series

                # Use existing function to group episodes by series and create Anime objects
                try:
                    anime_list = _group_episodes_by_series(episode_urls)

                    # Apply language, provider, and action to all anime objects
                    for anime in anime_list:
                        anime.language = language
                        anime.provider = provider
                        anime.action = "Download"
                        # Set language and provider on episodes too
                        for episode in anime.episode_list:
                            episode._selected_language = language
                            episode._selected_provider = provider

                except Exception as e:
                    logging.error(f"Failed to process episode URLs: {e}")
                    anime_list = []

                if not anime_list:
                    return jsonify({
                        'success': False,
                        'error': 'No valid anime objects could be created from provided URLs'
                    }), 400

                # Initialize progress tracking
                anime_title = data.get('anime_title', 'Unknown Anime')
                total_anime = len(anime_list)
                self.download_progress.update({
                    'active': True,
                    'anime_title': anime_title,
                    'total_episodes': total_anime,
                    'completed_episodes': 0,
                    'current_episode': 'Starting download...',
                    'start_time': time.time()
                })

                # Create wrapper function for download
                def download_anime_wrapper(anime_list, progress_callback=None):
                    """Wrapper function for downloading anime using existing functions"""
                    from ..execute import execute
                    import os
                    from .. import config
                    from .. import parser

                    # Update the global arguments with our output directory if specified
                    original_output_dir = None
                    if (self.arguments and
                        hasattr(self.arguments, 'output_dir') and
                        self.arguments.output_dir is not None):
                        # Save the original value to restore later
                        original_output_dir = getattr(parser.arguments, 'output_dir', None)
                        parser.arguments.output_dir = self.arguments.output_dir
                        download_dir = str(self.arguments.output_dir)
                    else:
                        download_dir = str(getattr(config, 'DEFAULT_DOWNLOAD_PATH', os.path.expanduser('~/Downloads')))

                    successful_downloads = 0
                    failed_downloads = 0

                    try:
                        for i, anime in enumerate(anime_list):
                            episode = anime.episode_list[0] if anime.episode_list else None
                            episode_info = ""
                            if episode:
                                episode_info = f" Episode {episode.episode} (Season {episode.season})"

                            if progress_callback:
                                progress_callback(i, f"Downloading{episode_info}")

                            try:
                                # Check if files exist before download
                                import glob
                                from pathlib import Path
                                from ..action.common import sanitize_filename

                                # Create expected file pattern
                                sanitized_title = sanitize_filename(anime.title)
                                anime_dir = Path(download_dir) / sanitized_title

                                # Count files before download
                                files_before = 0
                                if anime_dir.exists():
                                    files_before = len(list(anime_dir.glob('*')))

                                # Execute the download
                                from ..execute import _execute_single_anime
                                _execute_single_anime(anime)

                                # Count files after download
                                files_after = 0
                                if anime_dir.exists():
                                    files_after = len(list(anime_dir.glob('*')))

                                # Check if any new files were created
                                if files_after > files_before:
                                    successful_downloads += 1
                                    logging.info(f"Download completed for {episode_info}")
                                else:
                                    failed_downloads += 1
                                    logging.warning(f"Download failed for {episode_info} - no files created (language/provider unavailable)")

                            except Exception as episode_err:
                                failed_downloads += 1
                                logging.error(f"Download failed for {episode_info}: {episode_err}")

                        # Determine final status with better error messages
                        if successful_downloads == 0 and failed_downloads > 0:
                            if failed_downloads == 1:
                                error_msg = f'Download failed: The selected language/provider combination is not available for this episode.'
                            else:
                                error_msg = f'Download failed: No episodes downloaded. The selected language/provider combination is not available for any of the {failed_downloads} episode(s).'
                            if progress_callback:
                                progress_callback(0, error_msg, True)
                            result = False
                        elif failed_downloads > 0:
                            warning_msg = f'Partially completed: {successful_downloads} of {successful_downloads + failed_downloads} episode(s) downloaded. {failed_downloads} failed due to language/provider unavailability.'
                            if progress_callback:
                                progress_callback(successful_downloads, warning_msg, True)
                            result = True
                        else:
                            if progress_callback:
                                progress_callback(len(anime_list), f'Completed! Successfully downloaded {successful_downloads} episode(s)', True)
                            logging.info(f"Download completed for {successful_downloads} episode(s)")
                            result = True

                    except Exception as download_err:
                        logging.error(f"Download wrapper failed: {download_err}")
                        if progress_callback:
                            progress_callback(0, f'Download failed: {str(download_err)}', True)
                        result = False

                    finally:
                        # Restore original arguments if we modified them
                        if original_output_dir is not None:
                            parser.arguments.output_dir = original_output_dir

                    return result

                # Start download in background thread
                import threading

                def download_task():
                    def progress_update(completed, message, completed_flag=False):
                        self.download_progress.update({
                            'current_episode': message,
                            'completed_episodes': completed,
                            'active': not completed_flag
                        })

                    download_anime_wrapper(anime_list, progress_update)

                thread = threading.Thread(target=download_task)
                thread.daemon = True
                thread.start()

                return jsonify({
                    'success': True,
                    'message': f'Download started for {total_anime} episode(s)',
                    'episode_count': total_anime,
                    'language': language,
                    'provider': provider
                })

            except Exception as err:
                logging.error(f"Download error: {err}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to start download: {str(err)}'
                }), 500

        @self.app.route('/api/download-path')
        def api_download_path():
            """Get download path endpoint."""
            try:
                # Use arguments.output_dir if available, otherwise fall back to default
                download_path = str(config.DEFAULT_DOWNLOAD_PATH)
                if (self.arguments and
                    hasattr(self.arguments, 'output_dir') and
                    self.arguments.output_dir is not None):
                    download_path = str(self.arguments.output_dir)

                return jsonify({
                    'path': download_path
                })
            except Exception as err:
                logging.error(f"Failed to get download path: {err}")
                return jsonify({
                    'path': str(config.DEFAULT_DOWNLOAD_PATH)
                }), 500

        @self.app.route('/api/episodes', methods=['POST'])
        def api_episodes():
            """Get episodes for a series endpoint."""
            try:
                from flask import request
                data = request.get_json()
                if not data or 'series_url' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Series URL is required'
                    }), 400

                series_url = data['series_url']

                # Create wrapper function to handle all logic
                def get_episodes_for_series(series_url):
                    """Wrapper function using existing functions to get episodes"""
                    from ..common import get_season_episode_count
                    from ..entry import _detect_site_from_url
                    from .. import config

                    # Extract slug and site using existing functions
                    site = _detect_site_from_url(series_url)

                    if '/anime/stream/' in series_url:
                        slug = series_url.split('/anime/stream/')[-1].rstrip('/')
                        stream_path = 'anime/stream'
                        base_url = config.ANIWORLD_TO
                    elif '/serie/stream/' in series_url:
                        slug = series_url.split('/serie/stream/')[-1].rstrip('/')
                        stream_path = 'serie/stream'
                        base_url = config.S_TO
                    else:
                        raise ValueError('Invalid series URL format')

                    # Use existing function to get season/episode counts
                    season_counts = get_season_episode_count(slug, base_url)

                    # Build episodes structure
                    episodes_by_season = {}
                    for season_num, episode_count in season_counts.items():
                        if episode_count > 0:
                            episodes_by_season[season_num] = []
                            for ep_num in range(1, episode_count + 1):
                                episodes_by_season[season_num].append({
                                    'season': season_num,
                                    'episode': ep_num,
                                    'title': f"Episode {ep_num}",
                                    'url': f"{base_url}/{stream_path}/{slug}/staffel-{season_num}/episode-{ep_num}"
                                })

                    # Fallback if no seasons found
                    if not episodes_by_season:
                        episodes_by_season[1] = [{
                            'season': 1,
                            'episode': 1,
                            'title': 'Episode 1',
                            'url': f"{base_url}/{stream_path}/{slug}/staffel-1/episode-1"
                        }]

                    return episodes_by_season, slug

                # Use the wrapper function
                try:
                    episodes_by_season, slug = get_episodes_for_series(series_url)
                except ValueError as e:
                    return jsonify({
                        'success': False,
                        'error': str(e)
                    }), 400
                except Exception as e:
                    logging.error(f"Failed to get episodes: {e}")
                    return jsonify({
                        'success': False,
                        'error': 'Failed to fetch episodes'
                    }), 500

                return jsonify({
                    'success': True,
                    'episodes': episodes_by_season,
                    'slug': slug
                })

            except Exception as err:
                logging.error(f"Episodes fetch error: {err}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to fetch episodes: {str(err)}'
                }), 500

        @self.app.route('/api/progress')
        def api_progress():
            """Get download progress endpoint."""
            return jsonify({
                'active': self.download_progress['active'],
                'anime_title': self.download_progress['anime_title'],
                'total_episodes': self.download_progress['total_episodes'],
                'completed_episodes': self.download_progress['completed_episodes'],
                'current_episode': self.download_progress['current_episode'],
                'percentage': round((self.download_progress['completed_episodes'] / max(1, self.download_progress['total_episodes'])) * 100, 1) if self.download_progress['total_episodes'] > 0 else 0
            })

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in human readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours}h {minutes}m {seconds}s"

    def run(self):
        """Run the Flask web application."""
        logging.info("Starting AniWorld Downloader Web Interface...")
        logging.info(f"Server running at http://{self.host}:{self.port}")

        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=False  # Disable reloader to avoid conflicts
            )
        except KeyboardInterrupt:
            logging.info("Web interface stopped by user")
        except Exception as err:
            logging.error(f"Error running web interface: {err}")
            raise


def create_app(host='127.0.0.1', port=5000, debug=False, arguments=None) -> WebApp:
    """
    Factory function to create web application.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
        arguments: Command line arguments object

    Returns:
        WebApp instance
    """
    return WebApp(host=host, port=port, debug=debug, arguments=arguments)


def start_web_interface(arguments=None, port=5000, debug=False):
    """Start the web interface with configurable settings."""
    web_app = create_app(port=port, debug=debug, arguments=arguments)
    web_app.run()


if __name__ == '__main__':
    start_web_interface()