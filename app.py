from flask import Flask, request, jsonify

from py_processing.agregar_logo_a_imagen import apply_watermark
from py_processing.video import agregar_logo_a_video

app = Flask(__name__)


@app.route("/agregar_logo_a_imagen", methods=["POST"])
def agregar_logo():
    """{ "base_path": "C:/Users/Camilo/Desktop/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/Screenshot_2026-09-26-13-12-05-201_com.miui.gallery.jpg",
        "scale": 0.30,
        "opacity": 0.80,
        "margin": 0.02,
        "tolerance": 60,
        "bg_color": null,
        "position":"right"}"""
    parametros = request.get_json()
    resultado = apply_watermark(**parametros)
    return jsonify(resultado)


@app.route("/agregar_logo_a_video", methods=["POST"])
def ruta_agregar_logo_a_video():

    parametros = request.get_json()

    resultado = agregar_logo_a_video(parametros)

    return jsonify(resultado)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)