import importlib.util
import json
import os
import sys
from pathlib import Path

import ffmpeg
import pytest
from google.cloud import storage


# La carpeta del job contiene main.py y sus módulos importados.
JOB_DIR = (
    Path(__file__).resolve().parents[3]
    / "jobs"
    / "astro_video_processing"
)

# main.py importa módulos hermanos con imports absolutos.
# Agregar esta carpeta al path permite importarlos desde el test.
sys.path.insert(0, str(JOB_DIR))

# Cargar main.py como módulo para poder llamar ejecutar() directamente.
spec = importlib.util.spec_from_file_location(
    "astro_video_processing_main",
    JOB_DIR / "main.py",
)
main_job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_job)


def descargar_archivo(bucket, ruta_remota, workspace):
    """
    Descarga un archivo del bucket de pruebas y devuelve su ruta local.

    Se reemplazan las barras de la ruta remota para crear un nombre local
    plano, siguiendo el patrón usado por el test del logo.
    """
    nombre_local = ruta_remota.replace("/", "___")
    ruta_local = workspace / nombre_local

    bucket.blob(
        f"volume-cloud-run/{ruta_remota}"
    ).download_to_filename(str(ruta_local))

    return ruta_local


def preparar_entrada():
    """
    Lee JOB_PAYLOAD, descarga las entradas y crea el JSON que main.py espera:

        {
            "tasks": [
                {
                    "elementos": [...],
                    "audio": "...",
                    ...
                }
            ]
        }
    """
    payload = json.loads(os.environ["UNIR_PAYLOAD"])
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    bucket = storage.Client().bucket(bucket_name)

    # Descargar las imágenes y videos, y sustituir las rutas del payload
    # por las rutas locales correspondientes.
    elementos_locales = []

    for elemento in payload["elementos"]:
        ruta_local = descargar_archivo(
            bucket=bucket,
            ruta_remota=elemento["path"],
            workspace=workspace,
        )

        elementos_locales.append({
            **elemento,
            "path": str(ruta_local),
        })

    # Descargar el archivo de audio.
    audio_local = descargar_archivo(
        bucket=bucket,
        ruta_remota=payload["audio"],
        workspace=workspace,
    )

    # Definir una salida local para que pytest pueda verificarla.
    carpeta_salida = workspace / "salida_procesos"
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    ruta_salida = carpeta_salida / "video_unido_test.mp4"

    # La tarea conserva los demás parámetros del payload, por ejemplo
    # inicio_audio y fps, y reemplaza las rutas remotas por rutas locales.
    tarea = {
        **payload,
        "elementos": elementos_locales,
        "audio": str(audio_local),
        "salida": str(ruta_salida),
    }

    # main.py espera un archivo JSON con una lista bajo la clave "tasks".
    configuracion = {
        "tasks": [tarea],
    }

    ruta_configuracion = workspace / "config_unir.json"

    with ruta_configuracion.open("w", encoding="utf-8") as archivo:
        json.dump(configuracion, archivo, indent=2)

    return ruta_configuracion, ruta_salida


@pytest.mark.unir
def test_main_job_unir(monkeypatch):
    ruta_configuracion, ruta_salida = preparar_entrada()

    # Simular las variables y argumentos que recibiría el proceso del job.
    monkeypatch.setenv("CLOUD_RUN_TASK_INDEX", "0")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--modo",
            "unir_vid_img_aud",
            "--tasks-json",
            str(ruta_configuracion),
        ],
    )

    # Ejecutar el flujo real de main.py dentro del proceso actual de pytest.
    main_job.ejecutar()

    # Confirmar que se generó un MP4 con streams de video y audio.
    assert ruta_salida.is_file()
    assert ruta_salida.stat().st_size > 0

    metadatos = ffmpeg.probe(str(ruta_salida))
    tipos_stream = {
        stream["codec_type"]
        for stream in metadatos["streams"]
    }

    assert "video" in tipos_stream
    assert "audio" in tipos_stream