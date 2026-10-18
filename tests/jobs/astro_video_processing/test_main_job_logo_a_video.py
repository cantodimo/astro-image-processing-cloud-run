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

    # Descargar el video.
    video_name = payload["video"]
    local_video = video_name.replace("/", "___")
    video_path = os.path.join(workspace, local_video)

    video_blob = bucket.blob(
        f"volume-cloud-run/{video_name}"
    )
    video_blob.download_to_filename(video_path)

    # Descargar el logo.
    logo_path = os.path.join(
        workspace,
        "imagenes_base",
        "prueba_logotipo.png",
    )

    os.makedirs(os.path.dirname(logo_path), exist_ok=True)

    logo_blob = bucket.blob(
        "volume-cloud-run/imagenes_base/prueba_logotipo.png"
    )
    logo_blob.download_to_filename(logo_path)

    # Preparar la salida.
    output_dir = os.path.join(workspace, "salida_procesos")
    os.makedirs(output_dir, exist_ok=True)

    filename_without_extension = os.path.splitext(
        os.path.basename(video_name)
    )[0]

    output_path = os.path.join(
        output_dir,
        f"{filename_without_extension}_con_logo.mp4",
    )

    # Crear el archivo de configuración para main.sh.
    config = {
        "tasks": [
            {
                **payload,
                "video": video_path,
                "logo": logo_path,
                "output": output_path,
            }
        ]
    }

    config_path = os.path.join(workspace, "config_video.json")

    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)

    return config_path, output_path


def ejecutar_main(config_path, output_path):
    workspace = os.environ["GITHUB_WORKSPACE"]

    script = os.path.join(
        workspace,
        "jobs",
        "astro_video_processing",
        "main.sh",
    )

    env = os.environ.copy()
    env["CLOUD_RUN_TASK_INDEX"] = "0"

    result = subprocess.run(
        ["sh", script, config_path],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, (
        f"Error al ejecutar main.sh.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert os.path.isfile(output_path)
    assert os.path.getsize(output_path) > 0

    return output_path


@pytest.mark.video
def test_main_video():
    config_path, output_path = preparar_entrada()
    ejecutar_main(config_path, output_path)