import argparse
import json
import os
import tempfile
from pathlib import Path

import ffmpeg
from PIL import Image, ImageDraw, ImageFont

from fractions import Fraction

from agregar_logo_a_video import ENCODERS

# La carpeta fonts está al lado de este script.
FONT_DIR = Path(__file__).resolve().parent / "fonts"

def render_text_image(text, font_path, fontsize_px, color, bg_color, max_width_px,
                      line_spacing=1.1, padding=12):
    """
    Renderiza el texto en una imagen RGBA con Pillow.
    - text: texto (puede contener '\n')
    - font_path: ruta a .ttf (o None para fuente por defecto)
    - fontsize_px: tamaño en píxeles (int)
    - color: color del texto (ej. "white" o "#FFFF00")
    - bg_color: None => transparente, o color string/tuple
    - max_width_px: ancho máximo en píxeles para realizar wrap de líneas
    - line_spacing: factor multiplicador entre líneas
    - padding: padding interno en px
    """
    # Crear fuente
    try:
        if font_path and os.path.isfile(font_path):
            font = ImageFont.truetype(font_path, fontsize_px)
        else:
            # intentar Arial u otra, si falla usar load_default
            try:
                font = ImageFont.truetype("arial.ttf", fontsize_px)
            except Exception:
                font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Helper para medir texto
    dummy_img = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(dummy_img)

    # Wrap manual por ancho en píxeles
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")  # línea vacía
            continue
        line = words[0]
        for w in words[1:]:
            test = line + " " + w
            #w_px = draw.textsize(test, font=font)[0]
            bbox = draw.textbbox((0, 0), test, font=font)
            w_px = bbox[2] - bbox[0]
            if w_px <= max_width_px:
                line = test
            else:
                lines.append(line)
                line = w
        lines.append(line)

    # Calcular ancho máximo real y altura total
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

    mode = "RGBA"
    if bg_color is None:
        bg = (0, 0, 0, 0)
    else:
        # convertir color a RGBA si es string simple
        try:
            # crear temporal para obtener RGBA desde Pillow
            tmp = Image.new("RGBA", (1, 1), bg_color)
            bg = tmp.getpixel((0, 0))
        except Exception:
            bg = (0, 0, 0, 255)

    img = Image.new(mode, (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    # Dibujar líneas
    y = padding
    for i, ln in enumerate(lines):
        draw.text((padding, y), ln, font=font, fill=color)
        y += int(line_heights[i] * line_spacing)

    return img

def agregar_texto(config):
    """
    Agrega las capas de texto de config["textos"] y conserva, en lo posible,
    la configuración de video de la entrada: codec, FPS, pixel format y bitrate.
    """
    video_path = str(config["video"])
    out_path = Path(config["output"])
    textos = config["textos"]

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Consultar tanto el stream de video como la duración y el audio.
    metadata = ffmpeg.probe(video_path)

    video_metadata = next(
        stream
        for stream in metadata["streams"]
        if stream["codec_type"] == "video"
    )

    video_w = int(video_metadata["width"])
    video_h = int(video_metadata["height"])
    video_duration = float(metadata["format"]["duration"])

    # Usar el mismo encoder correspondiente al codec de origen,
    # siguiendo el mapeo que ya usa agregar_logo.
    codec_fuente = video_metadata.get("codec_name")
    encoder = ENCODERS.get(codec_fuente, "libx264")

    formato_pixel = video_metadata.get("pix_fmt") or "yuv420p"
    bitrate = video_metadata.get("bit_rate")

    # Preferir el FPS promedio y recurrir al nominal si no está disponible.
    fps_salida = video_metadata.get("avg_frame_rate")

    if not fps_salida or fps_salida in {"N/A", "0/0"}:
        fps_salida = video_metadata.get("r_frame_rate")

    # Normalizar la fracción, por ejemplo, "30/1".
    if fps_salida and fps_salida not in {"N/A", "0/0"}:
        fps_salida = str(Fraction(fps_salida))
    else:
        fps_salida = None

    tiene_audio = any(
        stream.get("codec_type") == "audio"
        for stream in metadata["streams"]
    )

    entrada_video = ffmpeg.input(video_path)
    video_con_textos = entrada_video.video

    # Mantener las imágenes temporales disponibles hasta que termine FFmpeg.
    with tempfile.TemporaryDirectory() as temp_dir:
        for indice, opciones_texto in enumerate(textos):
            texto = opciones_texto["text"]

            # Los nombres de fuentes relativos se buscan junto al script,
            # dentro de la carpeta fonts.
            font_path = opciones_texto.get(
                "font_path",
                "CrayonLibre-Regular.ttf",
            )
            ruta_fuente = Path(font_path)

            if not ruta_fuente.is_absolute():
                ruta_fuente = FONT_DIR / ruta_fuente

            fontsize = float(opciones_texto.get("fontsize", 0.05))

            # Un tamaño <= 1 se interpreta como proporción de la altura.
            if fontsize <= 1:
                fontsize_px = max(8, int(video_h * fontsize))
            else:
                fontsize_px = int(fontsize)

            max_width_pct = float(
                opciones_texto.get("max_width_pct", 0.90)
            )
            max_text_w = int(video_w * max_width_pct) - 4

            # Pillow dibuja cada texto una sola vez como PNG RGBA.
            imagen_texto = render_text_image(
                text=texto,
                font_path=str(ruta_fuente),
                fontsize_px=fontsize_px,
                color=opciones_texto.get("color", "white"),
                bg_color=opciones_texto.get("bg_color"),
                max_width_px=max_text_w,
                line_spacing=float(opciones_texto.get("line_spacing", 1.12)),
                padding=int(opciones_texto.get("padding", 12)),
            )

            txt_w, txt_h = imagen_texto.size
            margin = float(opciones_texto.get("margin", 0.02))
            margin_px = int(video_h * margin)

            position = opciones_texto.get(
                "position",
                ["center", "bottom"],
            )

            # JSON representa position como lista.
            if isinstance(position, list):
                position = tuple(position)

            if isinstance(position, tuple) and len(position) == 2:
                horizontal, vertical = position

                if horizontal == "left":
                    x = margin_px
                elif horizontal == "right":
                    x = video_w - txt_w - margin_px
                else:
                    x = (video_w - txt_w) // 2

                if vertical == "top":
                    y = margin_px
                elif vertical == "center":
                    y = (video_h - txt_h) // 2
                else:
                    y = video_h - txt_h - margin_px
            else:
                # También permite coordenadas numéricas [x, y].
                x = int(position[0])
                y = int(position[1])

            ruta_png = Path(temp_dir) / f"texto_{indice}.png"
            imagen_texto.save(ruta_png, format="PNG")

            # FFmpeg repite la imagen y la superpone al video.
            entrada_texto = ffmpeg.input(
                str(ruta_png),
                loop=1,
                framerate=fps_salida or 24,
            )

            video_con_textos = ffmpeg.overlay(
                video_con_textos,
                entrada_texto.video,
                x=x,
                y=y,
                shortest=1,
                format="auto",
            )

        # Empezar con las opciones de codificación que reflejan el origen.
        opciones_salida = {
            "vcodec": encoder,
            "pix_fmt": formato_pixel,
            "movflags": "+faststart",
            "map_metadata": 0,
        }

        # Mantener el FPS original cuando FFprobe lo reportó.
        if fps_salida:
            opciones_salida["r"] = fps_salida

        # Igual que agregar_logo: conservar el bitrate de video cuando existe.
        if bitrate and bitrate not in {"N/A", "0"}:
            opciones_salida["video_bitrate"] = int(bitrate)
        else:
            # FFprobe no siempre entrega el bitrate del stream.
            # CRF 18 prioriza calidad alta si no hay bitrate de origen disponible.
            opciones_salida["crf"] = int(config.get("crf", 18))

        # Mantener el comportamiento de audio que usa agregar_logo.
        streams_salida = [video_con_textos]

        if tiene_audio:
            streams_salida.append(entrada_video.audio)
            opciones_salida["acodec"] = "aac"
            opciones_salida["audio_bitrate"] = "192k"

        resultado = ffmpeg.output(
            *streams_salida,
            str(out_path),
            **opciones_salida,
        )

        resultado.overwrite_output().run()

    print(f"Video generado: {out_path}")
    return str(out_path)

def leer_argumentos():
    parser = argparse.ArgumentParser(
        description="Agrega una o más capas de texto a un video."
    )

    grupo_config = parser.add_mutually_exclusive_group(required=True)

    grupo_config.add_argument(
        "--config-json",
        help="Ruta a un archivo JSON con la configuración.",
    )
    grupo_config.add_argument(
        "--config",
        help="Configuración completa escrita como una cadena JSON.",
    )

    return parser.parse_args()


def ejecutar():
    #python poner_texto_a_video.py --config '{"video":"C:\Users\Camilo\Documents\cosas_astronomia\fotos\2026-08-28_eclipse_lunar_albun\VID_20260827_205926.mp4","output":"salida.mp4","textos":[{"text":"Texto sobre el video","font_path":"CrayonLibre-Regular.ttf","position":["center","bottom"]}]}'
    args = leer_argumentos()

    if args.config_json:
        # Leer la configuración desde un archivo.
        with open(args.config_json, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)
    else:
        # Interpretar el argumento como el contenido JSON.
        config = json.loads(args.config)

    agregar_texto(config)


if __name__ == "__main__":
    ejecutar()