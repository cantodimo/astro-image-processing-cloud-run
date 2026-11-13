import os

from google.cloud import storage

def descargar_gcs(image_path, local_path):
    """Descarga la imagen del bucket a su ruta original dentro del workspace."""
    workspace = os.environ["GITHUB_WORKSPACE"]
    bucket_name = os.environ["GCP_BUCKET_VOLUME"]

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(f"volume-cloud-run/{image_path}")

    # Asegurar que exista la carpeta local antes de descargar.
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)


def preparar_entrada(payload, path):
    workspace = os.environ["GITHUB_WORKSPACE"]
    image_path = payload[path]

    # El payload contiene una ruta relativa, por ejemplo:
    # "2026-11-08_ngc225_forma_C/IMG_20261108_212119.jpg"
    local_path = os.path.join(workspace, image_path)

    # Si es una salida intermedia de la integración, ya debe existir localmente.
    if os.path.isfile(local_path):
        return payload

    # Si no existe, descargarla del bucket conservando sus carpetas.
    descargar_gcs(image_path, local_path)

    # No reemplazar payload[path]: debe seguir teniendo la ruta relativa original.
    return payload

def carpeta_de_salida(image_path):
    """Devuelve la carpeta original, sin el prefijo de una salida intermedia."""
    ruta = os.path.normpath(image_path).replace("\\", "/")
    partes = ruta.split("/")

    if partes[0] == "salida_procesos":
        partes = partes[1:]

    if len(partes) <= 1:
        return ""

    return os.path.join(*partes[:-1])