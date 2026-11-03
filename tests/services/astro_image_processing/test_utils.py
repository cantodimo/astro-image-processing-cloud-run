import json
import os

from google.cloud import storage

def descargar_gcs(image_path, local_image):
    workspace = os.environ["GITHUB_WORKSPACE"]
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(
        f"volume-cloud-run/{image_path}"
    )

    blob.download_to_filename(
        os.path.join(workspace, local_image)
    )

def preparar_entrada(payload, path):
    workspace = os.environ["GITHUB_WORKSPACE"]
    image_path = payload[path]

    # Una salida intermedia como "salida_procesos/foto.png"
    # ya está en el workspace: se conserva esa ruta.
    local_path = os.path.join(workspace, image_path)

    if os.path.isfile(local_path):
        return payload

    # Si no existe localmente, se asume que la ruta corresponde a GCS.
    local_image = image_path.replace("/", "___")
    local_path = os.path.join(workspace, local_image)

    if not os.path.isfile(local_path):
        descargar_gcs(image_path, local_image)

    payload[path] = local_image
    return payload
