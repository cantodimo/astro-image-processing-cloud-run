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

# Importar main.py para ejecutar su función dentro del proceso de pytest.
spec = importlib.util.spec_from_file_location(
    "astro_video_processing_main",
    JOB_DIR / "main.py",
)
main_job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_job)


def descargar_video(bucket, ruta_remota, workspace):
    """Descarga un video del bucket y devuelve su ruta local."""
    ruta_local = workspace / ruta_remota.replace("/", "___")

    bucket.blob(
        f"volume-cloud-run/{ruta_remota}"
    ).download_to_filename(str(ruta_local))

    return ruta_local


def preparar_entrada():
    """
    Descarga los videos indicados en COMPARAR_VIDEOS_PAYLOAD y prepara
    el JSON de tareas que espera main.py.
    """
    payload = json.loads(os.environ["COMPARAR_VIDEOS_PAYLOAD"])
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    bucket = storage.Client().bucket(bucket_name)

    ruta_top_local = descargar_video(
        bucket=bucket,
        ruta_remota=payload["top_video_path"],
        workspace=workspace,
    )
    ruta_bottom_local = descargar_video(
        bucket=bucket,
        ruta_remota=payload["bottom_video_path"],
        workspace=workspace,
    )

    carpeta_salida = workspace / "salida_procesos"
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    ruta_salida = carpeta_salida / payload.get( "output", "comparacion_videos_test.mp4")

    # Reemplazar las rutas del bucket por rutas locales para el test.
    tarea = {
        **payload,
        "top_video_path": str(ruta_top_local),
        "bottom_video_path": str(ruta_bottom_local),
        "output": str(ruta_salida),
    }

    ruta_configuracion = workspace / "config_comparar_videos.json"

    with ruta_configuracion.open("w", encoding="utf-8") as archivo:
        json.dump(
            {"tasks": [tarea]},
            archivo,
            indent=2,
        )

    return (
        ruta_configuracion,
        ruta_salida,
        ruta_top_local,
        ruta_bottom_local,
        payload.get("audio_mode", "none"),
    )


@pytest.mark.comparar_videos
def test_main_job_comparar_videos(monkeypatch):
    (
        ruta_configuracion,
        ruta_salida,
        ruta_top_local,
        ruta_bottom_local,
        audio_mode,
    ) = preparar_entrada()

    monkeypatch.setenv("CLOUD_RUN_TASK_INDEX", "0")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--modo",
            "comparar_videos",
            "--tasks-json",
            str(ruta_configuracion),
        ],
    )

    # Ejecutar main.py y comparar_videos() en el mismo proceso.
    main_job.ejecutar()

    assert ruta_salida.is_file()
    assert ruta_salida.stat().st_size > 0