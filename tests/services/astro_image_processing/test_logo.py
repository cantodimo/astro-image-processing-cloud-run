import json
import os

import pytest
from google.cloud import storage

from servicios.astro_image_processing.app import app
from tests.services.astro_image_processing.test_utils import (
    preparar_entrada,
    carpeta_de_salida,
)
import json

def ejecutar_logo(payload):
    client = app.test_client()

    response = client.post(
        "/agregar_logo_a_imagen",
        json=payload
    )

    assert response.status_code == 200

    filename = os.path.basename(payload["base_path"])
    filename_without_extension = os.path.splitext(filename)[0]

    carpeta_relativa = carpeta_de_salida(payload["base_path"])

    output = os.path.join(
        os.environ["GITHUB_WORKSPACE"],
        "salida_procesos",
        carpeta_relativa,
        f"{filename_without_extension}_con_logo.png"
    )

    assert os.path.isfile(output)

    return output


@pytest.mark.logo
def test_agregar_logo_a_imagen(payload=None):
    payload_recibido = payload is not None
    #payload = preparar_entrada_logo()
    if payload is None:
        payload= json.loads(os.environ["LOGO_PAYLOAD"])

    payload= preparar_entrada(payload, "base_path")
    payload= preparar_entrada(payload, "logo_path")

    output= ejecutar_logo(payload)
    
    #para que cuando se ejecute el test individual no retorne nada, o si no daria warnings
    if payload_recibido:
        return output