from flask import Flask, request, jsonify

from py_processing.agregar_logo_a_imagen import apply_watermark
from py_processing.poner_texto_imagen import add_text_to_image
from py_processing.reescalar_imagen import crop_image
from py_processing.comparar_imagenes import combine_images
import os

app = Flask(__name__)

def resolver_ruta(raiz, ruta):
    if os.path.isabs(ruta):
        return ruta

    return os.path.join(raiz, ruta)

## comentario para probar disparo workflow solo con modificar este archivo
@app.route("/agregar_logo_a_imagen", methods=["POST"])
def agregar_logo():
    """curl --request POST ^
  --header "Content-Type: application/json" ^
  --data "{\"base_path\":\"C:/Users/Camilo/Desktop/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/reiner_gamma_nasa.jpg\",\"scale\":0.30,\"opacity\":0.80,\"margin\":0.02,\"tolerance\":60,\"bg_color\":null,\"position\":\"right\"}" ^
  http://localhost:8080/agregar_logo_a_imagen"""

    parametros = request.get_json()

    if "K_SERVICE" in os.environ:
        # Cloud Run: el bucket está montado en /mnt/bucket
        raiz = "/mnt/bucket"

    elif "GITHUB_ACTIONS" in os.environ:
        # GitHub Actions: los archivos están bajo GITHUB_WORKSPACE
        raiz = os.environ["GITHUB_WORKSPACE"]

    else:
        # PC local
        raiz = None

    if raiz is not None:
        parametros["base_path"] = resolver_ruta(
            raiz,
            parametros["base_path"]
        )

        logo_path = parametros.get(
            "logo_path",
            "imagenes_base/prueba_logotipo.png"
        )
        parametros["logo_path"] = resolver_ruta(
            raiz,
            logo_path
        )

        parametros["output_prefix"] = os.path.join(
            raiz,
            "salida_procesos"
        )

    else:
        # PC
        parametros["logo_path"] = (
            r"C:/Users/Camilo/Desktop/cosas_astronomia/imagenes_base/prueba_logotipo.png"
        )
        parametros["output_prefix"] = (
            r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/"
        )        

    resultado = apply_watermark(**parametros)
    return jsonify(resultado)


@app.route("/poner_texto_a_imagen", methods=["POST"])
def ruta_poner_texto_a_imagen():
    """
    curl --request POST ^
  --header "Content-Type: application/json" ^
  --data "{\"image_path\":\"C:/Users/Camilo/Desktop/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/reiner_gamma_nasa.jpg\",\"text\":\"Foto de la NASA\",\"fontsize\":0.03,\"color\":\"skyblue\",\"position\":[\"center\",\"top\"],\"margin\":0.05,\"max_width_pct\":0.92,\"font_path\":\"Jupiteroid-Regular.ttf\"}" ^
  http://localhost:8080/poner_texto_a_imagen
    """
    parametros = request.get_json()
    if isinstance(parametros.get("position"), list):
        parametros["position"] = tuple(parametros["position"])

    if "K_SERVICE" in os.environ:
        # Cloud Run
        parametros["output_prefix"] = "/mnt/bucket/salida_procesos/"
        parametros["image_path"] = "/mnt/bucket/" + parametros["image_path"]

    elif "GITHUB_ACTIONS" in os.environ:
        workspace = os.environ["GITHUB_WORKSPACE"]
        parametros["output_prefix"] = os.path.join(
            workspace, "salida_procesos"
        )
        parametros["image_path"] = os.path.join(
            workspace, parametros["image_path"]
        )

    else:
        # PC
        parametros["output_prefix"] = r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/"
        

    resultado = add_text_to_image(**parametros)
    return jsonify(resultado)

@app.route("/reescalar_imagen", methods=["POST"])
def ruta_reescalar_imagen():
    parametros = request.get_json()

    if "K_SERVICE" in os.environ:
        parametros["output_prefix"] = "/mnt/bucket/salida_procesos/"
        parametros["image_path"] = "/mnt/bucket/" + parametros["image_path"]

    elif "GITHUB_ACTIONS" in os.environ:
        workspace = os.environ["GITHUB_WORKSPACE"]
        parametros["output_prefix"] = os.path.join(
            workspace, "salida_procesos"
        )
        parametros["image_path"] = os.path.join(
            workspace, parametros["image_path"]
        )

    else:
        parametros["output_prefix"] = (
            r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/"
        )

    resultado = crop_image(**parametros)
    return jsonify(resultado)


@app.route("/comparar_imagenes", methods=["POST"])
def ruta_comparar_imagenes():
    parametros = request.get_json()

    if "K_SERVICE" in os.environ:
        # Cloud Run: las imágenes están bajo /mnt/bucket.
        parametros["top_image_path"] = os.path.join(
            "/mnt/bucket",
            parametros["top_image_path"]
        )
        parametros["bottom_image_path"] = os.path.join(
            "/mnt/bucket",
            parametros["bottom_image_path"]
        )
        parametros["output_prefix"] = "/mnt/bucket/salida_procesos/"

    elif "GITHUB_ACTIONS" in os.environ:
        # GitHub Actions: las imágenes están bajo GITHUB_WORKSPACE.
        workspace = os.environ["GITHUB_WORKSPACE"]

        parametros["top_image_path"] = os.path.join(
            workspace,
            parametros["top_image_path"]
        )
        parametros["bottom_image_path"] = os.path.join(
            workspace,
            parametros["bottom_image_path"]
        )
        parametros["output_prefix"] = os.path.join(
            workspace,
            "salida_procesos"
        )

    else:
        # PC local: conserva las rutas de entrada recibidas en el JSON.
        parametros["output_prefix"] = (
            r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/"
        )

    resultado = combine_images(**parametros)
    return jsonify(resultado)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)