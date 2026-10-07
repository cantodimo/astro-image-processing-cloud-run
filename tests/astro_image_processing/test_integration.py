import json
import os

import pytest
from google.cloud import storage

from tests.astro_image_processing.test_logo import ejecutar_logo, preparar_entrada
from tests.astro_image_processing.test_texto import ejecutar_texto


@pytest.mark.integration
def test_logo_y_texto():

    logo_payload = preparar_entrada()
    logo_output = ejecutar_logo(logo_payload)

    # ---------------------------------------------------------
    # Usar la salida del logo como entrada del texto
    # ---------------------------------------------------------
    
    logo_filename = os.path.basename(logo_output)

    texto_payload = json.loads(os.environ["TEXT_PAYLOAD"])
    texto_payload["image_path"] = os.path.join(
        "salida_procesos",
        logo_filename
    )

    ejecutar_texto(texto_payload)
