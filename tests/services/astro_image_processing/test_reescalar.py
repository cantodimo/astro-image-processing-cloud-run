import json
import os

import pytest
from google.cloud import storage
from PIL import Image

from servicios.astro_image_processing.app import app
from tests.services.astro_image_processing.test_utils import (
    preparar_entrada,
    carpeta_de_salida,
)
import json

def ejecutar_reescalar(payload):
    client = app.test_client()

    response = client.post(
        "/reescalar_imagen",
        json=payload
    )

    assert response.status_code == 200

    filename = os.path.basename(payload["image_path"])
    filename_without_extension = os.path.splitext(filename)[0]

    carpeta_relativa = carpeta_de_salida(payload["image_path"])

    output = os.path.join(
        os.environ["GITHUB_WORKSPACE"],
        "salida_procesos",
        carpeta_relativa,
        f"{filename_without_extension}_reescalada.png"
    )

    assert os.path.isfile(output)

    with Image.open(output) as image:
        assert image.size == (
            payload.get("target_width", 1080),
            payload.get("target_height", 1920)
        )

    return output


@pytest.mark.reescalar
def test_reescalar_y_cortar(payload=None):
    payload_recibido = payload is not None
    #payload = preparar_entrada_reescalar()
    if payload is None:
        payload= json.loads(os.environ["REESCALAR_PAYLOAD"])

    payload= preparar_entrada(payload, "image_path")

    output= ejecutar_reescalar(payload)
    
    #para que cuando se ejecute el test individual no retorne nada, o si no daria warnings
    if payload_recibido:
        return output