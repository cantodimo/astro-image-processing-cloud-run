from PIL import Image
import argparse
import os


def crop_vertical_section(image, start_pct, end_pct):
    """
    Conserva una sección vertical de la imagen usando porcentajes.

    Por ejemplo, start_pct=20 y end_pct=70 conserva desde el 20 %
    hasta el 70 % de la altura original.
    """

    if not 0 <= start_pct < end_pct <= 100:
        raise ValueError(
            "Los porcentajes deben cumplir: "
            "0 <= start_pct < end_pct <= 100"
        )

    image_width, image_height = image.size

    # Convertir los porcentajes de altura en coordenadas de píxeles.
    top = round(image_height * start_pct / 100)
    bottom = round(image_height * end_pct / 100)

    # Asegurar que el recorte tenga al menos un píxel de alto.
    bottom = max(top + 1, bottom)

    return image.crop(
        (0, top, image_width, bottom)
    )


def resize_to_width(image, target_width):
    """
    Ajusta el ancho de una imagen manteniendo su relación de aspecto.
    """

    if image.width == target_width:
        return image

    # Calcular el alto proporcional para evitar deformar la imagen.
    scale = target_width / image.width
    target_height = round(image.height * scale)

    return image.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS
    )


def combine_images(
    top_image_path,
    bottom_image_path,
    output_prefix=None,
    top_start_pct=20,
    top_end_pct=70,
    bottom_start_pct=20,
    bottom_end_pct=70
):
    """
    Recorta dos secciones verticales, ajusta sus anchos y las apila.

    La imagen más angosta se redimensiona proporcionalmente para que
    ambos recortes tengan el mismo ancho.
    """

    if output_prefix is None:
        output_prefix = os.path.dirname(top_image_path) or "."

    os.makedirs(output_prefix, exist_ok=True)

    top_filename = os.path.splitext(
        os.path.basename(top_image_path)
    )[0]
    bottom_filename = os.path.splitext(
        os.path.basename(bottom_image_path)
    )[0]

    output_path = os.path.join(
        output_prefix,
        f"{top_filename}_sobre_{bottom_filename}.png"
    )

    print("Imagen superior:", top_image_path)
    print("Imagen inferior:", bottom_image_path)
    print("Salida:", output_path)

    # Abrir ambas imágenes en RGBA para conservar transparencias.
    top_image = Image.open(top_image_path).convert("RGBA")
    bottom_image = Image.open(bottom_image_path).convert("RGBA")

    print("Tamaño original superior:", top_image.size)
    print("Tamaño original inferior:", bottom_image.size)

    # Recortar cada imagen usando sus propios porcentajes verticales.
    top_crop = crop_vertical_section(
        top_image,
        start_pct=top_start_pct,
        end_pct=top_end_pct
    )

    bottom_crop = crop_vertical_section(
        bottom_image,
        start_pct=bottom_start_pct,
        end_pct=bottom_end_pct
    )

    # El recorte más angosto se amplía proporcionalmente al ancho mayor.
    target_width = max(top_crop.width, bottom_crop.width)

    top_crop = resize_to_width(
        top_crop,
        target_width
    )

    bottom_crop = resize_to_width(
        bottom_crop,
        target_width
    )

    # La altura final es la suma de las alturas de ambos recortes.
    output_height = top_crop.height + bottom_crop.height

    resultado = Image.new(
        "RGBA",
        (target_width, output_height),
        (0, 0, 0, 0)
    )

    # Colocar un recorte arriba y el otro debajo.
    resultado.alpha_composite(top_crop, (0, 0))
    resultado.alpha_composite(
        bottom_crop,
        (0, top_crop.height)
    )

    resultado.save(output_path)

    print("Recorte superior ajustado:", top_crop.size)
    print("Recorte inferior ajustado:", bottom_crop.size)
    print("Tamaño final:", resultado.size)
    print("Guardado:", output_path)

    return output_path


if __name__ == "__main__":

    #python comparar_imagenes.py "C:/Users/Camilo/Documents/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/pez_raya.jpg" "C:/Users/Camilo/Documents/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/Screenshot_2026-09-26-13-12-05-201_com_con_logo.png" --top-start-pct 20 --top-end-pct 70 --bottom-start-pct 10 --bottom-end-pct 65
    parser = argparse.ArgumentParser(
        description=(
            "Recorta dos secciones verticales, iguala sus anchos "
            "sin deformarlas y las une en una sola imagen."
        )
    )

    parser.add_argument(
        "top_image",
        help="Ruta de la imagen que aparecerá arriba"
    )

    parser.add_argument(
        "bottom_image",
        help="Ruta de la imagen que aparecerá abajo"
    )

    parser.add_argument(
        "--output-prefix",
        default=r"C:/Users/Camilo/Documents/cosas_astronomia/salida_procesos/",
        help="Carpeta para guardar el resultado"
    )

    parser.add_argument(
        "--top-start-pct",
        type=float,
        default=0,
        help="Inicio del recorte superior, como porcentaje de su altura"
    )

    parser.add_argument(
        "--top-end-pct",
        type=float,
        default=100,
        help="Fin del recorte superior, como porcentaje de su altura"
    )

    parser.add_argument(
        "--bottom-start-pct",
        type=float,
        default=0,
        help="Inicio del recorte inferior, como porcentaje de su altura"
    )

    parser.add_argument(
        "--bottom-end-pct",
        type=float,
        default=100,
        help="Fin del recorte inferior, como porcentaje de su altura"
    )

    args = parser.parse_args()

    combine_images(
        top_image_path=args.top_image,
        bottom_image_path=args.bottom_image,
        output_prefix=args.output_prefix,
        top_start_pct=args.top_start_pct,
        top_end_pct=args.top_end_pct,
        bottom_start_pct=args.bottom_start_pct,
        bottom_end_pct=args.bottom_end_pct
    )