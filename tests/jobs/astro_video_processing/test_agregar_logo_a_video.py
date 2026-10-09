import json
import os
import subprocess

import pytest
from google.cloud import storage


def preparar_entrada():
    payload = json.loads(os.environ["JOB_PAYLOAD"])

    workspace = os.environ["GITHUB_WORKSPACE"]
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Construir la ruta del video dentro del bucket.
    video_name = payload["video"]
    video_path = video_name
    local_video = video_path.replace("/", "___")

    video_blob = bucket.blob(
        f"volume-cloud-run/{video_path}"
    )
    video_blob.download_to_filename(
        os.path.join(workspace, local_video)
    )

    # Descargar el logo.
    logo_blob = bucket.blob(
        "volume-cloud-run/imagenes_base/prueba_logotipo.png"
    )

    os.makedirs(
        os.path.join(workspace, "imagenes_base"),
        exist_ok=True,
    )

    logo_path = os.path.join(
        workspace,
        "imagenes_base",
        "prueba_logotipo.png",
    )

    logo_blob.download_to_filename(logo_path)

    # Preparar la salida.
    os.makedirs(
        os.path.join(workspace, "salida_procesos"),
        exist_ok=True,
    )

    filename_without_extension = os.path.splitext(video_name)[0]

    output_path = os.path.join(
        workspace,
        "salida_procesos",
        f"{filename_without_extension}_con_logo.mp4",
    )

    return {
        **payload,
        "video_path": os.path.join(workspace, local_video),
        "logo_path": logo_path,
        "output_path": output_path,
    }


def ejecutar_logo(payload):
    workspace = os.environ["GITHUB_WORKSPACE"]

    script = os.path.join(
        workspace,
        "jobs",
        "astro_video_processing",
        "agregar_logo_a_video.sh",
    )

    # Ejecutar el script con los 10 parámetros obligatorios.
    result = subprocess.run(
        [
            "sh",
            script,
            payload["video_path"],
            payload["logo_path"],
            payload["output_path"],
            str(payload["target_width"]),
            str(payload["target_height"]),
            str(payload["scale"]),
            str(payload["opacity"]),
            str(payload["margin"]),
            str(payload["fps"]),
            payload["position"],
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Error al procesar el video.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert os.path.isfile(payload["output_path"])
    assert os.path.getsize(payload["output_path"]) > 0

    return payload["output_path"]


@pytest.mark.video
def test_agregar_logo_a_video():
    payload = preparar_entrada()
    ejecutar_logo(payload)