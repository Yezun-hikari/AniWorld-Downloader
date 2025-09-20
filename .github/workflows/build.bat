@echo off
setlocal enabledelayedexpansion

set CURRENT_DIR=%cd%
cd ..\..

python -m pip install -U pip
pip install -U nuitka imageio
pip install -U -e .

rem Extract JSON_PATH
for /f "delims=" %%i in ('python -c "import fake_useragent, os; print(os.path.join(os.path.dirname(fake_useragent.__file__), 'data', 'browsers.jsonl'))"') do set JSON_PATH=%%i

rem Extract version
for /f "delims=" %%i in ('python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"') do set VERSION=%%i

rem Get the current year
for /f "delims=" %%i in ('powershell -Command "(Get-Date).Year"') do set YEAR=%%i

rem Display the extracted information
echo JSON_PATH: !JSON_PATH!
echo Version: !VERSION!
echo Year: !YEAR!

python src/aniworld/nuitka/preprocess.py

python -m nuitka ^
    --onefile ^
    --assume-yes-for-downloads ^
    --include-package=aniworld ^
    --include-data-file="!JSON_PATH!=fake_useragent/data/browsers.jsonl" ^
    --include-data-file=src/aniworld/ASCII.txt=aniworld/ASCII.txt ^
    --include-data-file=src/aniworld/aniskip/scripts/aniskip.lua=aniworld/aniskip/scripts/aniskip.lua ^
    --include-data-file=src/aniworld/aniskip/scripts/autostart.lua=aniworld/aniskip/scripts/autostart.lua ^
    --include-data-file=src/aniworld/aniskip/scripts/autoexit.lua=aniworld/aniskip/scripts/autoexit.lua ^
    --output-filename="aniworld-!VERSION!-windows_x64" ^
    --company-name="Phoenixthrush UwU" ^
    --product-name="AniWorld Downloader" ^
    --file-version="!VERSION!" ^
    --product-version="!VERSION!" ^
    --file-description="AniWorld Downloader is a command-line tool for downloading and streaming content from aniworld.to and s.to." ^
    --copyright="Copyright (c) 2024-!YEAR! phoenixthrush, Tmaster055" ^
    --windows-icon-from-ico=src/aniworld/nuitka/icon.webp ^
    src/aniworld/entry.py

cd /d "%CURRENT_DIR%"