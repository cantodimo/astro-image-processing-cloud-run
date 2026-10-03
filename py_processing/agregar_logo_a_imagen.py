from PIL import Image
import numpy as np
import os


# =========================================================
# CONFIGURACIÓN
# =========================================================

# Rutas para ejecución local
LOGO_LOCAL = r"C:/Users/Camilo/Desktop/cosas_astronomia/imagenes_base/prueba_logotipo.png"
PATH_PREFIX_LOCAL = r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/"

# Ruta donde estará montado el volumen en Cloud Run
VOLUME_PATH = "/mnt/bucket"

# Rutas relativas dentro del bucket
LOGO_CLOUD = "imagenes_base/prueba_logotipo.png"
PATH_PREFIX_CLOUD = "salida_procesos/"


# =========================================================
# DETECTAR ENTORNO
# =========================================================

IS_CLOUD_RUN = "K_SERVICE" in os.environ

if IS_CLOUD_RUN:
    LOGO = os.path.join(VOLUME_PATH, LOGO_CLOUD)
    PATH_PREFIX = os.path.join(VOLUME_PATH, PATH_PREFIX_CLOUD)
else:
    LOGO = LOGO_LOCAL
    PATH_PREFIX = PATH_PREFIX_LOCAL


def resolve_input_path(path):
    """
    En local:
        devuelve la ruta de Windows tal como viene.

    En Cloud Run:
        si se recibe una ruta relativa, la busca dentro del volumen.
    """

    if IS_CLOUD_RUN and not os.path.isabs(path):
        return os.path.join(VOLUME_PATH, path)

    return path

def analyze_alpha(img):
    img = img.convert("RGBA")
    a = img.split()[3]
    arr = np.array(a)
    total = arr.size
    transparent = int((arr == 0).sum())
    pct = 100.0 * transparent / total
    return pct, total, transparent

def make_transparent_by_color(logo, bg_color=None, tolerance=60):
    logo = logo.convert("RGBA")

    if bg_color is None:
        bg_color = logo.getpixel((0, 0))[:3]

    arr = np.array(logo)
    rgb = arr[:, :, :3].astype(int)
    bg = np.array(bg_color).astype(int)
    dist = ((rgb - bg) ** 2).sum(axis=2) ** 0.5
    mask = (dist > tolerance).astype(np.uint8) * 255
    alpha = arr[:, :, 3].astype(np.uint8)
    new_alpha = (alpha * (mask / 255.0)).astype(np.uint8)
    arr[:, :, 3] = new_alpha
    return Image.fromarray(arr, mode="RGBA")


def apply_watermark(
    base_path,
    scale=0.20,
    opacity=0.30,
    margin=0.02,
    tolerance=60,
    bg_color=None,
    position="right"
):

    """
    scale: ancho del logo como fracción del ancho de la imagen base
           ej. 0.2 = 20%

    opacity: 0..1
             ej. 0.3 = 30% opaco

    margin: fracción del tamaño de la imagen base
            ej. 0.02 = 2%

    position:
        "right" -> esquina inferior derecha
        "left"  -> esquina inferior izquierda
    """

    # Resolver ruta de entrada
    base_path = resolve_input_path(base_path)

    # Nombre del archivo de salida
    filename = os.path.basename(base_path)
    filename_without_extension = os.path.splitext(filename)[0]

    out_path = os.path.join(
        PATH_PREFIX,
        filename_without_extension + "_con_logo.jpg"
    )

    # Crear directorio de salida si no existe
    os.makedirs(PATH_PREFIX, exist_ok=True)

    print("Entorno:", "Cloud Run" if IS_CLOUD_RUN else "Local")
    print("Imagen:", base_path)
    print("Logo:", LOGO)
    print("Salida:", out_path)

    base = Image.open(base_path).convert("RGBA")
    logo = Image.open(LOGO)

    print("Logo mode original:", logo.mode)

    # Analizar transparencia
    pct, total, transparent = analyze_alpha(logo)

    print(
        f"Transparencia inicial: "
        f"{pct:.2f}% ({transparent}/{total} píxeles transparentes)"
    )

    # Si prácticamente no tiene transparencia, intentar eliminar
    # el fondo usando el color de la esquina superior izquierda
    logo = logo.convert("RGBA")

    if pct < 1.0:
        print(
            "Poca o nula transparencia detectada "
            "→ intentar quitar fondo por color..."
        )

        logo = make_transparent_by_color(
            logo,
            bg_color=bg_color,
            tolerance=tolerance
        )

        pct2, _, transparent2 = analyze_alpha(logo)

        print(
            f"Transparencia tras conversión: "
            f"{pct2:.2f}% ({transparent2}/{total})"
        )

    # Redimensionar manteniendo proporción
    w_logo = int(base.width * scale)
    h_logo = int(logo.height * (w_logo / logo.width))

    logo = logo.resize(
        (w_logo, h_logo),
        Image.LANCZOS
    )

    # Ajustar opacidad
    alpha = logo.split()[3]

    alpha = alpha.point(
        lambda p: int(p * opacity)
    )

    logo.putalpha(alpha)

    # Márgenes
    margin_x = int(base.width * margin)
    margin_y = int(base.height * margin)

    # Posición
    position = position.lower()

    if position == "left":
        x = margin_x

    elif position == "right":
        x = base.width - logo.width - margin_x

    else:
        raise ValueError(
            "position debe ser 'left' o 'right'"
        )

    y = base.height - logo.height - margin_y

    # Crear overlay
    overlay = Image.new(
        "RGBA",
        base.size,
        (0, 0, 0, 0)
    )

    overlay.paste(
        logo,
        (x, y),
        logo
    )

    # Combinar
    resultado = Image.alpha_composite(
        base,
        overlay
    )

    # Guardar como JPEG
    resultado = resultado.convert("RGB")

    resultado.save(
        out_path,
        "JPEG",
        quality=100
    )

    print("Guardado:", out_path)
    return out_path

# =========================================================
# PRUEBA LOCAL
# =========================================================

if __name__ == "__main__":
    base = r"C:/Users/Camilo/Desktop/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/Screenshot_2026-09-26-13-12-05-201_com.miui.gallery.jpg"

    apply_watermark(
        base,
        scale=0.30,
        opacity=0.80,
        margin=0.02,
        tolerance=60,
        bg_color=None,
        position="right"
    )