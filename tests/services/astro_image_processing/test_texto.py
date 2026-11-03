import json
import os

import pytest
from google.cloud import storage

from servicios.astro_image_processing.app import app
from tests.services.astro_image_processing.test_utils import preparar_entrada
import json

#def preparar_entrada_texto(payload=json.loads(os.environ["TEXT_PAYLOAD"])):
#    payload= preparar_entrada(payload, "image_path")
#    return payload

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
def test_poner_texto_a_imagen(payload=None):
    payload_recibido = payload is not None
    #payload = preparar_entrada_texto()
    if payload is None:
        payload= json.loads(os.environ["TEXT_PAYLOAD"])

    payload= preparar_entrada(payload, "image_path")

    output= ejecutar_texto(payload)

    #para que cuando se ejecute el test individual no retorne nada, o si no daria warnings
    if payload_recibido:
        return output