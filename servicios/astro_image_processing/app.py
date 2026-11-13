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

def configurar_entrada_y_salida(parametros, campo_imagen):
    """
    Convierte la ruta relativa recibida en una ruta local de entrada y
    mantiene su carpeta relativa debajo de salida_procesos.
    """
    ruta_relativa = parametros[campo_imagen]

    if "K_SERVICE" in os.environ:
        # Cloud Run tiene el bucket montado en /mnt/bucket.
        raiz = "/mnt/bucket"
    elif "GITHUB_ACTIONS" in os.environ:
        # GitHub Actions usa el checkout como raíz de los archivos.
        raiz = os.environ["GITHUB_WORKSPACE"]
    else:
        # En local se conserva la raíz de fotos usada actualmente.
        raiz = r"C:/Users/Camilo/Desktop/cosas_astronomia/fotos"

    ruta_entrada = parametros[campo_imagen]

    # La API recibe rutas relativas a la raíz del volumen.
    ruta_normalizada = os.path.normpath(ruta_entrada).replace("\\", "/")
    partes_ruta = ruta_normalizada.split("/")

    # Si otra operación generó esta imagen, su ruta empieza por
    # "salida_procesos/". Quitamos ese prefijo solo para calcular
    # la carpeta de salida; la ruta de entrada debe conservarse.
    if partes_ruta[0] == "salida_procesos":
        partes_carpeta = partes_ruta[1:-1]
    else:
        partes_carpeta = partes_ruta[:-1]

    carpeta_relativa = os.path.join(*partes_carpeta) if partes_carpeta else ""

    parametros["output_prefix"] = os.path.join(
        raiz,
        "salida_procesos",
        carpeta_relativa
    )

    # La ruta completa de entrada conserva "salida_procesos/" si ya era
    # una imagen intermedia de la integración.
    parametros[campo_imagen] = os.path.join(raiz, ruta_entrada)

    return raiz

## comentario para probar disparo workflow solo con modificar este archivo
@app.route("/agregar_logo_a_imagen", methods=["POST"])
def agregar_logo():
    """curl --request POST ^
  --header "Content-Type: application/json" ^
  --data "{\"base_path\":\"C:/Users/Camilo/Desktop/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/reiner_gamma_nasa.jpg\",\"scale\":0.30,\"opacity\":0.80,\"margin\":0.02,\"tolerance\":60,\"bg_color\":null,\"position\":\"right\"}" ^
  http://localhost:8080/agregar_logo_a_imagen"""

    parametros = request.get_json()

    raiz = configurar_entrada_y_salida(parametros, "base_path")

    logo_path = parametros.get(
        "logo_path",
        "imagenes_base/prueba_logotipo.png"
    )
    parametros["logo_path"] = resolver_ruta(raiz, logo_path)       

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
    
    _= configurar_entrada_y_salida(parametros, "image_path")

    if isinstance(parametros.get("position"), list):
        parametros["position"] = tuple(parametros["position"])
        
    resultado = add_text_to_image(**parametros)
    return jsonify(resultado)

@app.route("/reescalar_imagen", methods=["POST"])
def ruta_reescalar_imagen():
    parametros = request.get_json()

    _= configurar_entrada_y_salida(parametros, "image_path")

    resultado = crop_image(**parametros)
    return jsonify(resultado)


@app.route("/comparar_imagenes", methods=["POST"])
def ruta_comparar_imagenes():
    parametros = request.get_json()

    if "K_SERVICE" in os.environ:
        raiz = "/mnt/bucket"
    elif "GITHUB_ACTIONS" in os.environ:
        raiz = os.environ["GITHUB_WORKSPACE"]
    else:
        raiz = None

    if raiz is not None:
        # Las rutas del payload son relativas a la raíz del volumen.
        # Se conservan así para calcular la carpeta de salida.
        top_path = parametros["top_image_path"]
        bottom_path = parametros["bottom_image_path"]
        
        # Resolver las rutas locales de entrada sin cambiar sus rutas relativas.
        parametros["top_image_path"] = os.path.join(raiz, top_path)
        parametros["bottom_image_path"] = os.path.join(raiz, bottom_path)
        
        # Si la imagen superior viene de una operación anterior, su ruta será
        # "salida_procesos/carpeta/imagen.png". Para la nueva salida usamos
        # solo "carpeta", evitando duplicar "salida_procesos".
        ruta_top_normalizada = os.path.normpath(top_path).replace("\\", "/")
        partes_top = ruta_top_normalizada.split("/")
        
        if partes_top[0] == "salida_procesos":
            partes_carpeta = partes_top[1:-1]
        else:
            partes_carpeta = partes_top[:-1]
        
        carpeta_relativa = (
            os.path.join(*partes_carpeta)
            if partes_carpeta
            else ""
        )
        
        parametros["output_prefix"] = os.path.join(
            raiz,
            "salida_procesos",
            carpeta_relativa
        )
    else:
        parametros["output_prefix"] = (
            r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos"
        )

    resultado = combine_images(**parametros)
    return jsonify(resultado)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)