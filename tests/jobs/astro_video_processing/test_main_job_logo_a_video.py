import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from google.cloud import storage


# Ubicar el directorio del job para que main.py encuentre sus módulos.
JOB_DIR = (
    Path(__file__).resolve().parents[3]
    / "jobs"
    / "astro_video_processing"
)
sys.path.insert(0, str(JOB_DIR))

# Importar main.py como módulo para ejecutar su función directamente.
spec = importlib.util.spec_from_file_location(
    "astro_video_processing_main",
    JOB_DIR / "main.py",
)
main_job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_job)


def preparar_entrada():
    payload = json.loads(os.environ["LOGO_PAYLOAD"])

    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    bucket = storage.Client().bucket(bucket_name)

    # Descargar el video y usar una ruta local para la tarea.
    nombre_video = payload["video"]
    ruta_video_local = workspace / nombre_video.replace("/", "___")

    bucket.blob(
        f"volume-cloud-run/{nombre_video}"
    ).download_to_filename(str(ruta_video_local))

    # Descargar el logo que usa la prueba.
    ruta_logo_local = workspace / "imagenes_base" / "prueba_logotipo.png"
    ruta_logo_local.parent.mkdir(parents=True, exist_ok=True)

    bucket.blob(
        "volume-cloud-run/imagenes_base/prueba_logotipo.png"
    ).download_to_filename(str(ruta_logo_local))

    # Preparar la carpeta y el nombre del MP4 resultante.
    carpeta_salida = workspace / "salida_procesos"
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    nombre_sin_extension = Path(nombre_video).stem
    ruta_salida = carpeta_salida / f"{nombre_sin_extension}_con_logo.mp4"
    ruta_salida = carpeta_salida / payload.get( "output", f"{nombre_sin_extension}_con_logo.mp4")

    # main.py espera un JSON que contiene una lista llamada tasks.
    tarea = {
        **payload,
        "video": str(ruta_video_local),
        "logo": str(ruta_logo_local),
        "output": str(ruta_salida),
    }

    configuracion = {"tasks": [tarea]}
    ruta_configuracion = workspace / "config_video.json"

    with ruta_configuracion.open("w", encoding="utf-8") as archivo:
        json.dump(configuracion, archivo, indent=2)

    return ruta_configuracion, ruta_salida


@pytest.mark.logo
def test_main_job_logo(monkeypatch):
    ruta_configuracion, ruta_salida = preparar_entrada()

    # Simular las variables y argumentos con que se ejecuta main.py.
    monkeypatch.setenv("CLOUD_RUN_TASK_INDEX", "0")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--modo",
            "agregar_logo",
            "--tasks-json",
            str(ruta_configuracion),
        ],
    )

    # Ejecutar main.py en el proceso actual de pytest.
    main_job.ejecutar()

    assert ruta_salida.is_file()
    assert ruta_salida.stat().st_size > 0