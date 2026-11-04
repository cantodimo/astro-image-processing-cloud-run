#!/usr/bin/env bash
set -euo pipefail

echo "Instalando dependencias para las pruebas de astro_image_processing..."

# Instalar pytest y cliente gcs
python -m pip install --upgrade pip
python -m pip install pytest
python -m pip install google-cloud-storage

python -m pip install -r "$GITHUB_WORKSPACE/servicios/astro_image_processing/requirements.txt"

echo "Dependencias instaladas correctamente."