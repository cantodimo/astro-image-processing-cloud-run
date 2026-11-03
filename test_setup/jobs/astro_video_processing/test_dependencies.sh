#!/usr/bin/env bash
set -euo pipefail

echo "Instalando dependencias para las pruebas de astro_video_processing..."

# Instalar FFmpeg
sudo apt-get update
sudo apt-get install -y ffmpeg

# Instalar pytest y cliente gcs
python -m pip install --upgrade pip
python -m pip install pytest
python -m pip install google-cloud-storage

echo "Versiones instaladas:"
ffmpeg -version | head -n 1
pytest --version

python -m pip install -r "$GITHUB_WORKSPACE/jobs/astro_video_processing/requirements.txt"

echo "Dependencias instaladas correctamente."