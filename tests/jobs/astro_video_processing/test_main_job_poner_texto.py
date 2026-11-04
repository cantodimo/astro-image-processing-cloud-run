import importlib.util
import json
import os
import sys
from pathlib import Path

import ffmpeg
import pytest
from google.cloud import storage


# Ubicar el directorio del job para que main.py encuentre sus módulos.
JOB_DIR = (
    Path(__file__).resolve().parents[3]
    / "jobs"
    / "astro_video_processing"
)
sys.path.insert(0, str(JOB_DIR))

# Importar main.py para ejecutar ejecutar() dentro del proceso de pytest.
spec = importlib.util.spec_from_file_location(
    "astro_video_processing_main",
    JOB_DIR / "main.py",
)
main_job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_job)


def preparar_entrada():
    """
    Lee TEXTO_PAYLOAD, descarga el video de prueba y crea el archivo
    de tareas que espera main.py.
    """
    payload = json.loads(os.environ["TEXTO_PAYLOAD"])
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    bucket = storage.Client().bucket(bucket_name)

    # Descargar el video y usar su ruta local en la tarea.
    nombre_video = payload["video"]
    ruta_video_local = workspace / nombre_video.replace("/", "___")

    bucket.blob(
        f"volume-cloud-run/{nombre_video}"
    ).download_to_filename(str(ruta_video_local))

    # Definir una ruta local de salida para que el test pueda verificarla.
    carpeta_salida = workspace / "salida_procesos"
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    ruta_salida = carpeta_salida / "video_con_texto_test.mp4"

    # La tarea debe contener los mismos parámetros que recibe agregar_texto().
    tarea = {
        **payload,
        "video": str(ruta_video_local),
        "output": str(ruta_salida),
    }

    # main.py espera un JSON con una lista llamada tasks.
    ruta_configuracion = workspace / "config_poner_texto.json"

    with ruta_configuracion.open("w", encoding="utf-8") as archivo:
        json.dump({"tasks": [tarea]}, archivo, indent=2)

    return ruta_configuracion, ruta_salida


@pytest.mark.poner_texto
def test_main_job_poner_texto(monkeypatch):
    ruta_configuracion, ruta_salida = preparar_entrada()

    # Simular argumentos y variable de entorno del job.
    monkeypatch.setenv("CLOUD_RUN_TASK_INDEX", "0")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--modo",
            "poner_texto",
            "--tasks-json",
            str(ruta_configuracion),
        ],
    )

    # Ejecutar el flujo real de main.py y agregar_texto().
    main_job.ejecutar()

    assert ruta_salida.is_file()
    assert ruta_salida.stat().st_size > 0

    # Confirmar que FFmpeg generó una salida con stream de video.
    metadatos = ffmpeg.probe(str(ruta_salida))
    tipos_stream = {
        stream["codec_type"]
        for stream in metadatos["streams"]
    }

    assert "video" in tipos_stream