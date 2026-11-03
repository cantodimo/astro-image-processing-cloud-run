import json
import os

import pytest

from tests.services.astro_image_processing.test_logo import (
    test_agregar_logo_a_imagen as ejecutar_test_logo,
)
from tests.services.astro_image_processing.test_texto import (
    test_poner_texto_a_imagen as ejecutar_test_texto,
)
from tests.services.astro_image_processing.test_reescalar import (
    test_reescalar_y_cortar as ejecutar_test_reescalar,
)
from tests.services.astro_image_processing.test_comparar_imagenes import (
    test_comparar_imagenes as ejecutar_test_comparar_imagenes
)


OPERACIONES = {
    "logo": {
        "payload_env": "LOGO_PAYLOAD",
        "image_field": "base_path",
        "ejecutar": ejecutar_test_logo,
    },
    "texto": {
        "payload_env": "TEXT_PAYLOAD",
        "image_field": "image_path",
        "ejecutar": ejecutar_test_texto,
    },
    "reescalar": {
        "payload_env": "REESCALAR_PAYLOAD",
        "image_field": "image_path",
        "ejecutar": ejecutar_test_reescalar,
    },
    #este test tocaria ejecutarlo de primeras para poder controlar bien cual imagen va arriba y abajo,
    #pongo "image_field": "top_image_path" solo por compatibilidad por poderlo correr en cualquier orden
    "comparar_imagenes": {
        "payload_env": "COMPARAR_IMGS_PAYLOAD",
        "image_field": "top_image_path",
        "ejecutar": ejecutar_test_comparar_imagenes,
    },
}


@pytest.mark.integration
def test_integracion():
    steps = json.loads(os.environ["INTEGRATION_STEPS"])

    if not isinstance(steps, list) or not steps:
        raise ValueError("INTEGRATION_STEPS debe ser una lista no vacía")

    for nombre in steps:
        if nombre not in OPERACIONES:
            raise ValueError(f"Operación desconocida: {nombre}")

    workspace = os.environ["GITHUB_WORKSPACE"]
    current_image = None

    for nombre in steps:
        operacion = OPERACIONES[nombre]
        payload = json.loads(os.environ[operacion["payload_env"]])

        if current_image is not None:
            payload[operacion["image_field"]] = current_image

        output_path = operacion["ejecutar"](payload)

        if not output_path:
            raise RuntimeError(
                f"El test '{nombre}' no devolvió la ruta de salida"
            )

        current_image = os.path.relpath(output_path, workspace)