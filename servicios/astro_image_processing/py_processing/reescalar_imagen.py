from PIL import Image
import os


# =========================================================
# PROCESAMIENTO
# =========================================================

def crop_image(
    image_path,
    output_prefix=None,
    target_width=1080,
    target_height=1920,
    crop_offset_pct=0,
    mode="crop",
    resample=Image.LANCZOS
):
    """
    Cambia el tamaño de una imagen sin deformarla y permite
    desplazar el área de recorte.

    crop_offset_pct:
        -100 = alinear el recorte a la izquierda o arriba
           0 = centrar el recorte
         100 = alinear el recorte a la derecha o abajo

        Si el recorte es horizontal, el valor controla el desplazamiento
        izquierda/derecha.
        Si el recorte es vertical, controla el desplazamiento arriba/abajo.
    """

    if target_width <= 0 or target_height <= 0:
        raise ValueError(
            "target_width y target_height deben ser mayores que cero"
        )

    if not -100 <= crop_offset_pct <= 100:
        raise ValueError(
            "crop_offset_pct debe estar entre -100 y 100"
        )

    if output_prefix is None:
        output_prefix = os.path.dirname(image_path)

    filename = os.path.basename(image_path)
    filename_without_extension = os.path.splitext(filename)[0]

    out_path = os.path.join(
        output_prefix,
        filename_without_extension + "_reescalada.png"
    )

    os.makedirs(output_prefix, exist_ok=True)

    print("Imagen:", image_path)
    print("Salida:", out_path)
    print("Tamaño objetivo:", (target_width, target_height))
    print("Desplazamiento del recorte:", crop_offset_pct, "%")

    img = Image.open(image_path).convert("RGBA")

    image_width, image_height = img.size

    print("Tamaño original:", img.size)

    mode = mode.lower()

    if mode == "crop":
        # Escalar hasta cubrir el tamaño objetivo.
        # La imagen puede sobresalir en un eje; luego se recorta.
        if image_width / image_height > target_width / target_height:
            resized_height = target_height
            resized_width = round(
                image_width * target_height / image_height
            )
        else:
            resized_width = target_width
            resized_height = round(
                image_height * target_width / image_width
            )

        resized = img.resize(
            (resized_width, resized_height),
            resample
        )

        extra_x = resized_width - target_width
        extra_y = resized_height - target_height

        # 0 centra; los valores negativos desplazan hacia arriba/izquierda.
        left = round(
            extra_x / 2 + (extra_x / 2) * crop_offset_pct / 100
        )
        top = round(
            extra_y / 2 + (extra_y / 2) * crop_offset_pct / 100
        )

        left = max(0, min(left, extra_x))
        top = max(0, min(top, extra_y))

        right = left + target_width
        bottom = top + target_height

        resultado = resized.crop(
            (left, top, right, bottom)
        )

        print("Modo: recorte")
        print("Área recortada:", (left, top, right, bottom))

    elif mode == "pad":
        # Escalar hasta que toda la imagen quepa dentro del tamaño objetivo.
        # El espacio restante se completa con negro.
        scale = min(
            target_width / image_width,
            target_height / image_height
        )

        resized_width = round(image_width * scale)
        resized_height = round(image_height * scale)

        resized = img.resize(
            (resized_width, resized_height),
            resample
        )

        # Centrar la imagen reducida sobre un fondo negro.
        left = (target_width - resized_width) // 2
        top = (target_height - resized_height) // 2

        resultado = Image.new(
            "RGBA",
            (target_width, target_height),
            (0, 0, 0, 255)
        )

        # Usa el canal alfa como máscara para que cualquier transparencia
        # de la imagen también quede sobre el fondo negro.
        resultado.paste(
            resized,
            (left, top),
            resized
        )

        print("Modo: fondo negro")
        print("Imagen escalada:", resized.size)
        print("Posición sobre fondo:", (left, top))

    else:
        raise ValueError(
            "mode debe ser 'crop' o 'pad'"
        )

    print("Tamaño final:", resultado.size)

    resultado.save(
        out_path,
        "PNG"
    )

    print("Guardado:", out_path)

    return out_path

# =========================================================
# EJECUCIÓN DESDE LÍNEA DE COMANDOS
#python reescalar_imagen.py "C:\Users\Camilo\Documents\cosas_astronomia\fotos\2026-09-25-luna_reiner_gamma\IMG_20260925_200821.jpg"
# =========================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "image_path",
        help="Ruta de la imagen de entrada"
    )

    parser.add_argument(
        "--output-prefix",
        default=r"C:/Users/Camilo/Documents/cosas_astronomia/salida_procesos/",
        help="Carpeta donde se guardará la imagen de salida"
    )

    parser.add_argument(
        "--target-width",
        type=int,
        default=1080,
        help="Ancho final en píxeles"
    )

    parser.add_argument(
        "--target-height",
        type=int,
        default=1920,
        help="Alto final en píxeles"
    )

    parser.add_argument(
        "--crop_offset_pct",
        type=int,
        default=0,
        help="corrimiento porcentual del recorte para modo crop"
    )

    parser.add_argument(
        "--mode",
        choices=["crop", "pad"],
        default="crop",
        help=(
            "Modo de ajuste: 'crop' recorta el exceso; "
            "'pad' agrega fondo negro"
        )
    )

    args = parser.parse_args()

    crop_image(
        image_path=args.image_path,
        output_prefix=args.output_prefix,
        target_width=args.target_width,
        target_height=args.target_height,
        crop_offset_pct=args.crop_offset_pct,
        mode=args.mode
    )