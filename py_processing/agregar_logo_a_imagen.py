from PIL import Image
import numpy as np
import os


# =========================================================
# PROCESAMIENTO
# =========================================================

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
    position="right",
    logo_path=None,
    output_prefix=None
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

    # Nombre del archivo de salida
    filename = os.path.basename(base_path)
    filename_without_extension = os.path.splitext(filename)[0]

    out_path = os.path.join(
        output_prefix,
        #filename_without_extension + "_con_logo.jpg"
        filename_without_extension + "_con_logo.png"
    )

    # Crear directorio de salida si no existe
    os.makedirs(output_prefix, exist_ok=True)

    print("Imagen:", base_path)
    print("Logo:", logo_path)
    print("Salida:", out_path)

    base = Image.open(base_path).convert("RGBA")
    logo = Image.open(logo_path)

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
    #resultado = resultado.convert("RGB")

    #resultado.save(
    #    out_path,
    #    "JPEG",
    #    quality=100
    #)

    # Guardar como PNG
    resultado.save(
        out_path,
        "PNG"
    )

    print("Guardado:", out_path)
    return out_path


# =========================================================
# EJECUCIÓN DESDE LÍNEA DE COMANDOS
# =========================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "base",
        help="Ruta de la imagen base"
    )

    parser.add_argument(
        "--logo",
        required=False,
        default=r"C:/Users/Camilo/Desktop/cosas_astronomia/imagenes_base/prueba_logotipo.png"
    )

    parser.add_argument(
        "--output-prefix",
        required=False,
        default=r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/"
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=0.30
    )

    parser.add_argument(
        "--opacity",
        type=float,
        default=0.80
    )

    parser.add_argument(
        "--margin",
        type=float,
        default=0.02
    )

    parser.add_argument(
        "--tolerance",
        type=int,
        default=60
    )

    parser.add_argument(
        "--position",
        default="right"
    )

    args = parser.parse_args()

    apply_watermark(
        args.base,
        scale=args.scale,
        opacity=args.opacity,
        margin=args.margin,
        tolerance=args.tolerance,
        bg_color=None,
        position=args.position,
        logo_path=args.logo,
        output_prefix=args.output_prefix
    )