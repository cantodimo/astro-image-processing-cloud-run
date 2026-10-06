import json
import os

import pytest
from google.cloud import storage

from servicios.astro_image_processing.app import app



def preparar_entrada():
    payload = json.loads(os.environ["LOGO_PAYLOAD"])

    workspace = os.environ["GITHUB_WORKSPACE"]
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Descargar imagen indicada en el payload
    image_path = payload["base_path"]
    local_image = image_path.replace("/", "___")

    blob = bucket.blob(
        f"volume-cloud-run/{image_path}"
    )

    blob.download_to_filename(
        os.path.join(workspace, local_image)
    )

    # Descargar logo requerido por la prueba
    logo_blob = bucket.blob(
        "volume-cloud-run/imagenes_base/prueba_logotipo.png"
    )

    logo_blob.download_to_filename(
        os.path.join(
            workspace,
            "imagenes_base",
            "prueba_logotipo.png"
        )
    )

    # La aplicación espera el nombre de la imagen local
    payload["base_path"] = local_image

    return payload


def ejecutar_logo(payload):
    client = app.test_client()

    response = client.post(
        "/agregar_logo_a_imagen",
        json=payload
    )

    assert response.status_code == 200

    filename = os.path.basename(payload["base_path"])
    filename_without_extension = os.path.splitext(filename)[0]

    output = os.path.join(
        os.environ["GITHUB_WORKSPACE"],
        "salida_procesos",
        f"{filename_without_extension}_con_logo.png"
    )

    assert os.path.isfile(output)

    return output


@pytest.mark.logo
def test_agregar_logo_a_imagen():
    payload = preparar_entrada()

    ejecutar_logo(payload)