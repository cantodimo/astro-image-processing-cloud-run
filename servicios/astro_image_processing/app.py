from flask import Flask, request, jsonify

from py_processing.agregar_logo_a_imagen import apply_watermark
from py_processing.poner_texto_imagen import add_text_to_image
import os

app = Flask(__name__)

## comentario para probar disparo workflow solo con modificar este archivo
@app.route("/agregar_logo_a_imagen", methods=["POST"])
def agregar_logo():
    """curl --request POST ^
  --header "Content-Type: application/json" ^
  --data "{\"base_path\":\"C:/Users/Camilo/Desktop/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/reiner_gamma_nasa.jpg\",\"scale\":0.30,\"opacity\":0.80,\"margin\":0.02,\"tolerance\":60,\"bg_color\":null,\"position\":\"right\"}" ^
  http://localhost:8080/agregar_logo_a_imagen"""

    parametros = request.get_json()
    if "K_SERVICE" in os.environ:
        # Cloud Run
        parametros["logo_path"] = "/mnt/bucket/imagenes_base/prueba_logotipo.png"
        parametros["output_prefix"] = "/mnt/bucket/salida_procesos/"
        parametros["base_path"] = "/mnt/bucket/" + parametros["base_path"]

    elif "GITHUB_ACTIONS" in os.environ:
        workspace = os.environ["GITHUB_WORKSPACE"]
        parametros["logo_path"] = os.path.join(
            workspace, "imagenes_base", "prueba_logotipo.png"
        )
        parametros["output_prefix"] = os.path.join(
            workspace, "salida_procesos"
        )
        parametros["base_path"] = os.path.join(
            workspace, parametros["base_path"]
        )

    else:
        # PC
        parametros["logo_path"] = r"C:/Users/Camilo/Desktop/cosas_astronomia/imagenes_base/prueba_logotipo.png"
        parametros["output_prefix"] = r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/"
        

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



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)