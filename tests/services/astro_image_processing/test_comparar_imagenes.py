import json
import os

import pytest

from servicios.astro_image_processing.app import app
from tests.services.astro_image_processing.test_utils import preparar_entrada


def ejecutar_comparar(payload):
    client = app.test_client()

    response = client.post(
        "/comparar_imagenes",
        json=payload
    )

    assert response.status_code == 200

    top_filename = os.path.splitext(
        os.path.basename(payload["top_image_path"])
    )[0]

    bottom_filename = os.path.splitext(
        os.path.basename(payload["bottom_image_path"])
    )[0]

    output = os.path.join(
        os.environ["GITHUB_WORKSPACE"],
        "salida_procesos",
        f"{top_filename}_sobre_{bottom_filename}.png"
    )

    assert os.path.isfile(output)

    return output


@pytest.mark.comparar_imgs
def test_comparar_imagenes(payload=None):
    payload_recibido = payload is not None

    if payload is None:
        payload = json.loads(os.environ["COMPARAR_IMGS_PAYLOAD"])

    # Asegurar que las dos imágenes estén disponibles localmente.
    payload = preparar_entrada(payload, "top_image_path")
    payload = preparar_entrada(payload, "bottom_image_path")

    output = ejecutar_comparar(payload)

    # Permite que otro test utilice la imagen generada en una integración.
    if payload_recibido:
        return output