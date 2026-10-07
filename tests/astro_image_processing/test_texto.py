import json
import os

import pytest
from google.cloud import storage

from servicios.astro_image_processing.app import app


def ejecutar_texto(payload):
    client = app.test_client()

    response = client.post(
        "/poner_texto_a_imagen",
        json=payload
    )

    assert response.status_code == 200

    filename = os.path.basename(payload["image_path"])
    filename_without_extension = os.path.splitext(filename)[0]

    output = os.path.join(
        os.environ["GITHUB_WORKSPACE"],
        "salida_procesos",
        f"{filename_without_extension}_con_texto.png"
    )

    assert os.path.isfile(output)

    return output


@pytest.mark.texto
def test_poner_texto_a_imagen():
    payload = json.loads(os.environ["TEXT_PAYLOAD"])

    workspace = os.environ["GITHUB_WORKSPACE"]
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Descargar imagen indicada en el payload
    image_path = payload["image_path"]
    local_image = image_path.replace("/", "___")

    blob = bucket.blob(
        f"volume-cloud-run/{image_path}"
    )

    blob.download_to_filename(
        os.path.join(workspace, local_image)
    )

    # La app espera el nombre de la imagen local
    payload["image_path"] = local_image

    ejecutar_texto(payload)