<a id="readme-top"></a>
# AniWorld Downloader

AniWorld Downloader is a command-line tool for downloading and streaming content from aniworld.to and s.to. Currently available for Windows, macOS and Linux, it supports a variety of providers.

![PyPI Downloads](https://img.shields.io/pypi/dm/aniworld?label=downloads&color=blue)
![License](https://img.shields.io/pypi/l/aniworld?label=License&color=blue)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Features

- **Download Episodes or Seasons**: Effortlessly download individual episodes or entire seasons with a single command.
- **Stream Instantly**: Watch episodes directly using the integrated mpv player for a seamless experience.
- **Auto-Next Playback**: Enjoy uninterrupted viewing with automatic transitions to the next episode.
- **Multiple Providers**: Access a variety of streaming providers on aniworld.to for greater flexibility.
- **Language Preferences**: Easily switch between German Dub, English Sub, or German Sub to suit your needs.
- **Aniskip Support**: Automatically skip intros and outros for a smoother viewing experience.
- **Web Interface**: Modern web UI for easy anime searching, downloading, and queue management.
- **Docker Support**: Containerized deployment with Docker and Docker Compose for easy setup.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Installation

### Prerequisites

Ensure you have **[Python 3.9](https://www.python.org/downloads/)** or higher installed.<br>
Additionally, make sure **[Git](https://git-scm.com/downloads)** is installed if you plan to install the development version.


### Installation

#### Install Latest Stable Release (Recommended)

To install the latest stable version, use the following command:

```shell
pip install --upgrade aniworld
```

#### Install Latest Development Version (Requires Git)

To install the latest development version directly from GitHub, use the following command:

```shell
pip install --upgrade git+https://github.com/Master-T-v-T-v-T/AniWorld-Downloader.git@next#egg=aniworld
```

Re-run this command periodically to update to the latest development build. These builds are from the `next` branch and may include experimental or unstable changes.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


### Uninstallation

To uninstall AniWorld Downloader, run the following command:

```shell
pip --uninstall aniworld
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

AniWorld Downloader offers four versatile usage modes:

1. **Interactive Menu**: Launch the tool and navigate through an intuitive menu to select and manage downloads or streams.
2. **Web Interface**: Modern web UI for easy searching, downloading, and queue management with real-time progress tracking.
3. **Command-Line Arguments**: Execute specific tasks directly by providing arguments, such as downloading a particular episode or setting preferences.

Choose the method that best suits your workflow and enjoy a seamless experience!

### Menu Example

To start the interactive menu, simply run:

```shell
aniworld
```

### Web Interface

Launch the modern web interface for easy searching, downloading, and queue management:

```shell
aniworld --web-ui
```

The web interface provides:
- **Modern Search**: Search anime across aniworld.to and s.to with a sleek interface
- **Episode Selection**: Visual episode picker with season/episode organization
- **Download Queue**: Real-time download progress tracking
- **User Authentication**: Optional multi-user support with admin controls
- **Settings Management**: Configure providers, languages, and download preferences

#### Web Interface Options

```shell
# Basic web interface (localhost only)
aniworld --web-ui

# Expose to network (accessible from other devices)
aniworld --web-ui --web-expose

# Enable authentication for multi-user support
aniworld --web-ui --enable-web-auth

# Custom port and disable browser auto-open
aniworld --web-ui --web-port 3000 --no-browser

# Web interface with custom download directory
aniworld --web-ui --output-dir /path/to/downloads
```

### Command-Line Arguments Example

AniWorld Downloader provides a variety of command-line options for downloading and streaming anime without relying on the interactive menu. These options unlock advanced features such as `--aniskip`.

#### Example 1: Download a Single Episode

To download episode 1 of "Demon Slayer: Kimetsu no Yaiba":

```shell
aniworld --episode https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1
```

#### Example 2: Download Multiple Episodes

To download multiple episodes of "Demon Slayer":

```shell
aniworld --episode https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1 https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-2
```

#### Example 3: Watch Episodes with Aniskip

To watch an episode while skipping intros and outros:

```shell
aniworld --episode https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1 --action Watch --aniskip
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Anime4K Setup

Enhance your anime viewing experience with Anime4K. Follow the instructions below to configure Anime4K for use with the mpv player, even outside of AniWorld Downloader.

### For High-Performance GPUs
*(Examples: GTX 1080, RTX 2070, RTX 3060, RX 590, Vega 56, 5700XT, 6600XT, M1 Pro/Max/Ultra, M2 Pro/Max)*

Run the following command to optimize Anime4K for high-end GPUs:

```shell
aniworld --anime4k High
```

### For Low-Performance GPUs
*(Examples: GTX 980, GTX 1060, RX 570, M1, M2, Intel integrated GPUs)*

Run the following command to configure Anime4K for low-end GPUs:

```shell
aniworld --anime4k Low
```

### Uninstall Anime4K
To remove Anime4K from your setup, use this command:

```shell
aniworld --anime4k Remove
```

### Additional Information

All files for Anime4K are saved in the **mpv** directory during installation. 

- **Windows**: `C:\Users\<YourUsername>\AppData\Roaming\mpv`
- **macOS**: `/Users/<YourUsername>/.config/mpv`
- **Linux**: `/home/<YourUsername>/.config/mpv`

You can switch between `High` and `Low` modes at any time to match your GPU's performance. To cleanly uninstall Anime4K, use the `Remove` option.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Dependencies

AniWorld Downloader depends on the following Python packages:

- **`requests`**: For handling HTTP requests.
- **`beautifulsoup4`**: For parsing and scraping HTML content.
- **`yt-dlp`**: For downloading videos from supported providers.
- **`npyscreen`**: For creating interactive terminal-based user interfaces.
- **`tqdm`**: For providing progress bars during downloads.
- **`fake_useragent`**: For generating random user-agent strings.
- **`packaging`**: For parsing version numbers and handling package versions.
- **`jsbeautifier`**: Used for the Filemoon extractor.
- **`py-cpuinfo`**: Only required on Windows for gathering CPU information (AVX2 support for MPV).
- **`windows-curses`**: Required on Windows systems to enable terminal-based UI functionality.

These dependencies are automatically installed when you set up AniWorld Downloader using `pip`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Docker Deployment

AniWorld Downloader can be easily deployed using Docker for containerized environments.

### Using Docker Compose (Recommended)

1. Clone the repository:
   ```shell
   git clone https://github.com/Master-T-v-T-v-T/AniWorld-Downloader.git
   cd AniWorld-Downloader
   ```

2. Build and start the container:
   ```shell
   docker-compose up -d --build
   ```

### Using Docker Directly

```shell
# Build the image
docker build -t aniworld-downloader .

# Run the container
docker run -d \
  --name aniworld-downloader \
  -p 8080:8080 \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/data:/app/data \
  aniworld-downloader
```

### Docker Configuration

The Docker container runs with:
- **User Security**: Non-root user for enhanced security
- **System Dependencies**: Includes ffmpeg for video processing
- **Web Interface**: Enabled by default with authentication and network exposure
- **Download Directory**: `/app/downloads` (mapped to host)
- **Port**: 8080 (configurable via environment variables)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Credits

- **[mpv](https://github.com/mpv-player/mpv.git)**: A versatile media player used for seamless streaming.
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp.git)**: A powerful tool for downloading videos from various providers.
- **[Anime4K](https://github.com/bloc97/Anime4K)**: A cutting-edge real-time upscaler for enhancing anime video quality.
- **[Aniskip](https://api.aniskip.com/api-docs)**: Provides the opening and ending skip times for the Aniskip extension.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Support

If you need help with AniWorld Downloader, you can:

- **Submit an issue** on the [GitHub Issues](https://github.com/Master-T-v-T-v-T/AniWorld-Downloader/issues) page.

If you find AniWorld Downloader useful, consider starring the repository on GitHub. Your support is greatly appreciated and inspires continued development.

Thank you for using AniWorld Downloader!

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Legal Disclaimer

AniWorld Downloader is made for accessing content that’s already publicly available online. It doesn’t support or promote piracy or copyright violations. The developer isn’t responsible for how the tool is used or for any content found through external links.

All content accessed with AniWorld Downloader is available on the internet, and the tool itself doesn’t host or share copyrighted files. It also has no control over the accuracy, legality, or availability of the websites it links to.

If you have concerns about any content accessed through this tool, please reach out directly to the website’s owner, admin, or hosting provider. Thanks for your understanding.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

This project is licensed under the **[MIT License](LICENSE)**.  
For more details, see the LICENSE file.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
