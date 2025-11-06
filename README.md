<a id="readme-top"></a>
# AniWorld Downloader

AniWorld Downloader is a tool for downloading content from various streaming sites. It features a modern web interface and can be easily deployed using Docker.

![Downloads](https://img.shields.io/badge/Downloads-A_few-blue
)
![License](https://img.shields.io/pypi/l/aniworld?label=License&color=blue)

![Preview](.github/assets/preview.png)

## Table of Contents
- [Core Features](#core-features)
- [Supported Sites](#supported-sites)
- [Supported Hosters](#supported-hosters)
- [Installation](#installation)
- [Usage](#usage)
- [Docker Deployment](#docker-deployment)
- [API Endpoints](#api-endpoints)
- [Support](#support)
- [Legal Disclaimer](#legal-disclaimer)
- [License](#license)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Core Features

- **Web Interface**: A modern web UI for easy searching, downloading, and queue management with real-time progress tracking.
- **Docker Support**: Containerized deployment with Docker and Docker Compose for a quick and easy setup.
- **Download Queue**: Manage all your downloads in one place with a clear and organized queue.
- **Multiple Sources**: Download content from a variety of sources.
- **Custom Download Paths**: Set different download directories for series/anime and movies to keep your library organized.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Supported Sites

You can download content from the following websites:

- **AniWorld.to** (Anime)
- **S.to** (Anime & Series)
- **MegaKino.ms** (Movies)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Supported Hosters

The downloader supports a wide range of popular hosters, including:
- VOE
- Filemoon
- Vidmoly
- Doodstream
- Streamtape
- LoadX
- Luluvdo
- Vidoza
- SpeedFiles

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
pip install --upgrade git+https://github.com/Yezun-hikari/AniWorld-Downloader.git@next#egg=aniworld
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

The primary way to use this tool is through its web interface, especially when deployed with Docker.

### Web Interface

Launch the modern web interface for easy searching, downloading, and queue management:

```shell
aniworld --web-ui
```

The web interface provides:
- **Modern Search**: Search for anime, series, and movies across all supported sites.
- **Episode/Movie Selection**: A visual picker to select what you want to download.
- **Download Queue**: Track the real-time progress of all your downloads.
- **User Authentication**: Optional multi-user support with admin controls.
- **Settings Management**: Configure providers, languages, and download preferences.

#### Web Interface Options

```shell
# Basic web interface (localhost only)
aniworld --web-ui

# Expose to network (accessible from other devices)
aniworld --web-ui --web-expose

# Enable authentication for multi-user support
aniworld --web-ui --enable-web-auth

# Set custom download paths
aniworld --web-ui --output-dir /path/to/series-downloads --movie-dir /path/to/movie-downloads
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Docker Deployment

The recommended way to run the AniWorld Downloader is with Docker, which simplifies setup and dependency management.

### Using Docker Compose (Recommended)

1. Clone the repository:
   ```shell
   git clone https://github.com/Yezun-hikari/AniWorld-Downloader.git
   cd AniWorld-Downloader
   ```

2.  Modify `docker-compose.yml` to set your download paths. By default, it will create `downloads` and `movies` directories in the project folder.

3. Build and start the container:
   ```shell
   docker-compose up -d --build
   ```

### Docker Configuration

The Docker container runs with:
- **User Security**: Non-root user for enhanced security.
- **System Dependencies**: Includes ffmpeg for video processing.
- **Web Interface**: Enabled by default with authentication and network exposure.
- **Download Directories**:
    - `/app/downloads` (for series/anime)
    - `/app/movies` (for movies)
- **Port**: 8080 (configurable via environment variables)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Using Docker Compose with Gluetun VPN

For users who want to route the container's traffic through a VPN, you can use [Gluetun](https://github.com/qdm12/gluetun). Here is an example `docker-compose.yml` for a Portainer stack:

```yml
version: '3.8'
services:
  aniworld:
    container_name: aniworld-downloader
    image: aniworld-downloader:local
    volumes:
      - ./downloads:/app/downloads
      - ./movies:/app/movies
      - ./data:/app/data
    stdin_open: true
    tty: true
    restart: unless-stopped
    network_mode: "service:vpn"
  vpn:
    image: 'qmcgaw/gluetun'
    container_name: vpn
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER= # e.g., mullvad, nordvpn, protonvpn
      - OPENVPN_USER= # Your OpenVPN username
      - OPENVPN_PASSWORD= # Your OpenVPN password
    ports:
      - "8080:8080" # AniWorld WebUI
      - "8001:8000" # Gluetun API for integrations like gethomepage
    volumes:
      - ./gluetun:/gluetun
    restart: unless-stopped
```

In this setup:
- The `aniworld` service is configured to use the network of the `vpn` service (`network_mode: "service:vpn"`).
- The `vpn` service is a Gluetun container. You must configure the `VPN_SERVICE_PROVIDER` (e.g., Mullvad, NordVPN, ProtonVPN) and your credentials. For a full list of providers and setup instructions, refer to the [**official Gluetun documentation**](https://github.com/qdm12/gluetun-wiki/tree/main/setup/providers).
- **Port `8080`** exposes the AniWorld Downloader web interface.
- **Port `8001`** exposes the Gluetun API, which can be used for integrations with dashboards like [gethomepage](https://gethomepage.dev/).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## API Endpoints

The web interface provides a simple API to monitor download status, making it easy to integrate with dashboards like [gethomepage](https://gethomepage.dev/).

### `/api/download-status`

This endpoint provides real-time information about the currently active download.

- **URL**: `/api/download-status`
- **Method**: `GET`
- **Authentication**: None. This endpoint is publicly accessible.

#### Example Response

If a download is in progress, the API will return a JSON object like this:

```json
{
  "series_name": "Oshi No Ko",
  "current_episode_progress": "35%",
  "download_speed": "8.46MiB/s",
  "eta": "00:28",
  "overall_progress": "0/1",
  "success": true
}
```

If no download is active, it will return:

```json
{
  "success": false,
  "message": "No active downloads"
}
```

### gethomepage Integration

You can add a widget to your [gethomepage](https://gethomepage.dev/) dashboard to monitor your downloads. Add the following configuration to your `services.yaml` file:

```yaml
- AniWorld Downloader:
    icon: https://github.com/Yezun-hikari/AniWorld-Downloader/blob/main/src/aniworld/nuitka/icon.webp?raw=true
    href: http://localhost:8080/
    description: WebUI for Anime-Downloads
    widget:
      type: customapi
      url: http://localhost:8080/api/download-status
      mappings:
        - field: series_name
          label: Name
        - field: current_episode_progress
          label: Progress
        - field: download_speed
          label: Speed
        - field: overall_progress
          label: Episodes
        - field: eta
          label: ETA
```

**Note:** The `gethomepage` widget will only display the first four mapped fields on the dashboard.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Credits
Original AniWorld-Downloader: *[phoenixthrush](https://github.com/phoenixthrush)* <br/>
MEGAKino-Downloader: *[Tmaster055](https://github.com/Tmaster055)* <br/>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Support

If you need help with AniWorld Downloader, you can:

- **Submit an issue** on the [GitHub Issues](https://github.com/Yezun-hikari/AniWorld-Downloader/issues) page.

If you find this tool useful, consider starring the repository on GitHub. Your support is greatly appreciated!

Thank you for using AniWorld Downloader!

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## ⚠️ Legal Disclaimer

I provide this tool for educational and informational purposes only. You are solely responsible for how you use it. Any actions taken using this tool are entirely your own responsibility. I do not condone or support illegal use.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

This project is licensed under the **[MIT License](LICENSE)**.
For more details, see the LICENSE file or click the blue text above.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
