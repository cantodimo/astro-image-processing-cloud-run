from PIL import Image, ImageDraw, ImageFont
import os

##python poner_texto_imagen.py "C:/Users/Camilo/Desktop/cosas_astronomia/fotos/2026-09-25-luna_reiner_gamma/reiner_gamma_nasa.jpg" --text "PRUEBA DE PONER TEXTO" --fontsize 0.03 --color skyblue --position center top --margin 0.05 --max-width-pct 0.92

def render_text_image(
    text,
    font_path,
    fontsize_px,
    color,
    bg_color,
    max_width_px,
    line_spacing=1.1,
    padding=12
):
    """
    Renderiza el texto en una imagen RGBA con Pillow.

    - text: texto (puede contener '\\n')
    - font_path: ruta a .ttf (o None para fuente por defecto)
    - fontsize_px: tamaño en píxeles
    - color: color del texto
    - bg_color: None => transparente
    - max_width_px: ancho máximo del texto en píxeles
    - line_spacing: factor entre líneas
    - padding: padding interno en px
    """

    # Crear fuente
    try:
        if font_path and os.path.isfile(font_path):
            font = ImageFont.truetype(font_path, fontsize_px)
        else:
            try:
                font = ImageFont.truetype("arial.ttf", fontsize_px)
            except Exception:
                font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Imagen auxiliar para medir texto
    dummy_img = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(dummy_img)

    # =========================
    # WRAP DEL TEXTO
    # =========================

    lines = []

    for paragraph in text.split("\n"):
        words = paragraph.split()

        if not words:
            lines.append("")
            continue

        line = words[0]

        for w in words[1:]:
            test = line + " " + w

            bbox = draw.textbbox((0, 0), test, font=font)
            w_px = bbox[2] - bbox[0]

            if w_px <= max_width_px:
                line = test
            else:
                lines.append(line)
                line = w

        lines.append(line)

    # =========================
    # MEDIR TEXTO
    # =========================

    max_line_w = 0
    line_heights = []

    for ln in lines:

        bbox = draw.textbbox((0, 0), ln, font=font)

        w_px = bbox[2] - bbox[0]
        h_px = bbox[3] - bbox[1]

        line_heights.append(h_px)

        if w_px > max_line_w:
            max_line_w = w_px

    if max_line_w < 1:
        max_line_w = max_width_px

    total_h = int(sum(line_heights) * line_spacing)

    img_w = max_line_w + padding * 2
    img_h = total_h + padding * 2

    # =========================
    # FONDO
    # =========================

    if bg_color is None:
        bg = (0, 0, 0, 0)
    else:
        try:
            tmp = Image.new("RGBA", (1, 1), bg_color)
            bg = tmp.getpixel((0, 0))
        except Exception:
            bg = (0, 0, 0, 255)

    img = Image.new("RGBA", (img_w, img_h), bg)

    draw = ImageDraw.Draw(img)

    # =========================
    # DIBUJAR TEXTO
    # =========================

    y = padding

    for i, ln in enumerate(lines):

        draw.text(
            (padding, y),
            ln,
            font=font,
            fill=color
        )

        y += int(line_heights[i] * line_spacing)

    return img


def add_text_to_image(
    image_path,
    output_prefix=None,
    text="Texto de ejemplo",
    font_path=None,
    fontsize=0.05,
    color="white",
    bg_color=None,
    position=("center", "bottom"),
    margin=0.02,
    max_width_pct=0.90,
    padding=12
):
    """
    Agrega texto sobre una imagen y guarda el resultado.

    image_path:
        Ruta de la imagen de entrada.

    output_prefix:
        Carpeta donde se guardará la imagen resultante.

    fontsize:
        <= 1  -> fracción del alto de la imagen
        > 1   -> tamaño directamente en píxeles

    position:
        ("left"|"center"|"right",
         "top"|"center"|"bottom")

        También puede ser:
        (x, y)

    margin:
        separación del borde como fracción del alto.

    max_width_pct:
        ancho máximo del texto como fracción del ancho de la imagen.

    bg_color:
        None = fondo transparente para el texto.
    """

    # =========================
    # NOMBRE DE SALIDA
    # =========================

    filename = os.path.basename(image_path)
    filename_without_extension = os.path.splitext(filename)[0]

    out_path = os.path.join(
        output_prefix,
        filename_without_extension + "_con_texto.png"
    )

    # Crear directorio de salida si no existe
    os.makedirs(output_prefix, exist_ok=True)

    print("Imagen:", image_path)
    print("Salida:", out_path)

    # =========================
    # ABRIR IMAGEN
    # =========================

    img = Image.open(image_path).convert("RGBA")

    image_w, image_h = img.size

    # =========================
    # TAMAÑO DE FUENTE
    # =========================

    if fontsize <= 1:
        fontsize_px = max(8, int(image_h * float(fontsize)))
    else:
        fontsize_px = int(fontsize)

    # =========================
    # ANCHO MÁXIMO DEL TEXTO
    # =========================

    max_text_w = int(image_w * max_width_pct) - 4

    # =========================
    # CREAR IMAGEN DEL TEXTO
    # =========================

    text_img = render_text_image(
        text=text,
        font_path=font_path,
        fontsize_px=fontsize_px,
        color=color,
        bg_color=bg_color,
        max_width_px=max_text_w,
        line_spacing=1.12,
        padding=padding
    )

    txt_w, txt_h = text_img.size

    # =========================
    # MARGEN
    # =========================

    margin_px = int(image_h * margin)

    # =========================
    # CALCULAR POSICIÓN
    # =========================

    if isinstance(position, tuple) and isinstance(position[0], str):

        horiz, vert = position

        # X
        if horiz == "left":
            x = margin_px

        elif horiz == "center":
            x = (image_w - txt_w) // 2

        elif horiz == "right":
            x = image_w - txt_w - margin_px

        else:
            x = (image_w - txt_w) // 2

        # Y
        if vert == "top":
            y = margin_px

        elif vert == "center":
            y = (image_h - txt_h) // 2

        elif vert == "bottom":
            y = image_h - txt_h - margin_px

        else:
            y = image_h - txt_h - margin_px

    else:
        # Posición manual (x, y)
        x = int(position[0])
        y = int(position[1])

    # =========================
    # PEGAR TEXTO SOBRE IMAGEN
    # =========================

    img.alpha_composite(text_img, (x, y))

    # =========================
    # GUARDAR
    # =========================

    img.save(out_path)

    print("Guardado:", out_path)

    return out_path


# =========================================================
# EJECUCIÓN DESDE LÍNEA DE COMANDOS
# =========================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "image_path",
        help="Ruta de la imagen base"
    )

    parser.add_argument(
        "--output-prefix",
        default=r"C:/Users/Camilo/Desktop/cosas_astronomia/salida_procesos/",
        help="Carpeta donde se guardará la imagen de salida"
    )

    parser.add_argument(
        "--text",
        default="Texto de ejemplo",
        help="Texto que se agregará a la imagen"
    )

    parser.add_argument(
        "--font-path",
        default=None,
        help="Ruta al archivo .ttf"
    )

    parser.add_argument(
        "--fontsize",
        type=float,
        default=0.05,
        help="Tamaño de fuente. <=1 es fracción del alto; >1 son píxeles"
    )

    parser.add_argument(
        "--color",
        default="white",
        help="Color del texto"
    )

    parser.add_argument(
        "--bg-color",
        default=None,
        help="Color de fondo del texto. Por defecto transparente"
    )

    parser.add_argument(
        "--position",
        nargs=2,
        default=["center", "bottom"],
        help="Posición: left/center/right y top/center/bottom"
    )

    parser.add_argument(
        "--margin",
        type=float,
        default=0.02,
        help="Margen como fracción del alto de la imagen"
    )

    parser.add_argument(
        "--max-width-pct",
        type=float,
        default=0.90,
        help="Ancho máximo del texto como fracción del ancho"
    )

    parser.add_argument(
        "--padding",
        type=int,
        default=12,
        help="Padding interno del texto en píxeles"
    )

    args = parser.parse_args()

    # Convertir position de lista a tuple
    position = tuple(args.position)

    add_text_to_image(
        image_path=args.image_path,
        output_prefix=args.output_prefix,
        text=args.text,
        font_path=args.font_path,
        fontsize=args.fontsize,
        color=args.color,
        bg_color=args.bg_color,
        position=position,
        margin=args.margin,
        max_width_pct=args.max_width_pct,
        padding=args.padding
    )
