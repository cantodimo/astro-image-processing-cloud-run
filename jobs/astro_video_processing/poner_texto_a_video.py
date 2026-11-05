import argparse
import json
import os
import tempfile
from pathlib import Path

import ffmpeg
from PIL import Image, ImageDraw, ImageFont

from fractions import Fraction

from agregar_logo_a_video import ENCODERS
from helpers.reescalar import ajustar_video_a_lienzo

# La carpeta fonts está al lado de este script.
FONT_DIR = Path(__file__).resolve().parent / "fonts"

def render_text_image(
    text,
    font_path,
    fontsize_px,
    color,
    bg_color,
    max_width_px,
    line_spacing=1.1,
    padding=12,
):
    """
    Dibuja el texto en una imagen RGBA.

    Conserva las cajas medidas con textbbox para compensar el desplazamiento
    propio de algunas fuentes y evitar que se recorten sus letras.
    """
    # Cargar la fuente solicitada. Si no está disponible, intentar una
    # fuente del sistema y finalmente usar la fuente predeterminada de Pillow.
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

    imagen_medicion = Image.new("RGBA", (10, 10))
    draw_medicion = ImageDraw.Draw(imagen_medicion)

    # Separar por párrafos para respetar los saltos de línea explícitos
    # y ajustar las líneas al ancho disponible.
    lineas = []

    for parrafo in text.split("\n"):
        palabras = parrafo.split()

        if not palabras:
            lineas.append("")
            continue

        linea_actual = palabras[0]

        for palabra in palabras[1:]:
            candidata = f"{linea_actual} {palabra}"
            caja = draw_medicion.textbbox((0, 0), candidata, font=font)
            ancho_candidata = caja[2] - caja[0]

            if ancho_candidata <= max_width_px:
                linea_actual = candidata
            else:
                lineas.append(linea_actual)
                linea_actual = palabra

        lineas.append(linea_actual)

    # Guardar las cajas completas. Los valores left/top pueden ser negativos
    # y luego se compensan al dibujar.
    cajas_texto = []
    anchos_lineas = []
    altos_lineas = []

    for linea in lineas:
        caja = draw_medicion.textbbox((0, 0), linea, font=font)
        cajas_texto.append(caja)
        anchos_lineas.append(caja[2] - caja[0])
        altos_lineas.append(caja[3] - caja[1])

    ancho_texto = max(anchos_lineas, default=0)

    if ancho_texto < 1:
        ancho_texto = max_width_px

    alto_texto = int(sum(altos_lineas) * line_spacing)

    ancho_imagen = ancho_texto + padding * 2
    alto_imagen = alto_texto + padding * 2

    # Fondo transparente cuando bg_color es None.
    if bg_color is None:
        color_fondo = (0, 0, 0, 0)
    else:
        try:
            imagen_color = Image.new("RGBA", (1, 1), bg_color)
            color_fondo = imagen_color.getpixel((0, 0))
        except Exception:
            color_fondo = (0, 0, 0, 255)

    imagen_texto = Image.new(
        "RGBA",
        (ancho_imagen, alto_imagen),
        color_fondo,
    )
    draw = ImageDraw.Draw(imagen_texto)

    # Ubicar cada línea dentro del PNG compensando el left/top de su caja.
    y = padding

    for indice, linea in enumerate(lineas):
        caja = cajas_texto[indice]
        left, top, _, _ = caja

        draw.text(
            (padding - left, y - top),
            linea,
            font=font,
            fill=color,
        )

        y += int(altos_lineas[indice] * line_spacing)

    return imagen_texto

def _leer_datos_video(video_path):
    """
    Lee dimensiones de presentación, duración, codec, FPS, pixel format,
    bitrate y presencia de audio del video.
    """
    metadata = ffmpeg.probe(video_path)

    video_metadata = next(
        stream
        for stream in metadata["streams"]
        if stream["codec_type"] == "video"
    )

    ancho = int(video_metadata["width"])
    alto = int(video_metadata["height"])

    # FFmpeg suele guardar videos verticales como cuadros horizontales
    # acompañados por metadatos de rotación. Ajustar las dimensiones usadas
    # para calcular las coordenadas del texto.
    rotacion = video_metadata.get("tags", {}).get("rotate", 0)

    for dato in video_metadata.get("side_data_list", []):
        if "rotation" in dato:
            rotacion = dato["rotation"]
            break

    rotacion = round(float(rotacion)) % 360

    if rotacion in {90, 270}:
        ancho, alto = alto, ancho

    fps = video_metadata.get("avg_frame_rate")

    if not fps or fps in {"N/A", "0/0"}:
        fps = video_metadata.get("r_frame_rate")

    if fps and fps not in {"N/A", "0/0"}:
        fps = str(Fraction(fps))
    else:
        fps = None

    bitrate = video_metadata.get("bit_rate")

    tiene_audio = any(
        stream.get("codec_type") == "audio"
        for stream in metadata["streams"]
    )

    return {
        "metadata": metadata,
        "width": ancho,
        "height": alto,
        "duration": float(metadata["format"]["duration"]),
        "codec": video_metadata.get("codec_name"),
        "pixel_format": video_metadata.get("pix_fmt") or "yuv420p",
        "bitrate": bitrate,
        "fps": fps,
        "has_audio": tiene_audio,
    }

def _crear_capas_texto(video_stream, textos, datos_video, temp_dir):
    """
    Renderiza cada texto y lo superpone al stream de video.
    """
    video_w = datos_video["width"]
    video_h = datos_video["height"]
    fps = datos_video["fps"] or 24

    video_con_textos = video_stream

    for indice, opciones_texto in enumerate(textos):
        font_path = opciones_texto.get(
            "font_path",
            "CrayonLibre-Regular.ttf",
        )
        ruta_fuente = Path(font_path)

        if not ruta_fuente.is_absolute():
            ruta_fuente = FONT_DIR / ruta_fuente

        fontsize = float(opciones_texto.get("fontsize", 0.05))

        # Un valor <= 1 expresa el tamaño como proporción de la altura.
        if fontsize <= 1:
            fontsize_px = max(8, int(video_h * fontsize))
        else:
            fontsize_px = int(fontsize)

        max_width_pct = float(
            opciones_texto.get("max_width_pct", 0.90)
        )
        ancho_maximo_texto = int(video_w * max_width_pct) - 4

        imagen_texto = render_text_image(
            text=opciones_texto["text"],
            font_path=str(ruta_fuente),
            fontsize_px=fontsize_px,
            color=opciones_texto.get("color", "white"),
            bg_color=opciones_texto.get("bg_color"),
            max_width_px=ancho_maximo_texto,
            line_spacing=float(opciones_texto.get("line_spacing", 1.12)),
            padding=int(opciones_texto.get("padding", 12)),
        )

        texto_w, texto_h = imagen_texto.size
        position = opciones_texto.get(
            "position",
            ["center", "bottom"],
        )
        margin = float(opciones_texto.get("margin", 0.02))

        x, y = _calcular_posicion_texto(
            position=position,
            video_w=video_w,
            video_h=video_h,
            texto_w=texto_w,
            texto_h=texto_h,
            margin=margin,
        )

        ruta_png = Path(temp_dir) / f"texto_{indice}.png"
        imagen_texto.save(ruta_png, format="PNG")

        entrada_texto = ffmpeg.input(
            str(ruta_png),
            loop=1,
            framerate=fps,
        )

        video_con_textos = ffmpeg.overlay(
            video_con_textos,
            entrada_texto.video,
            x=x,
            y=y,
            shortest=1,
            format="auto",
        )

    return video_con_textos

def _crear_opciones_salida(config, datos_video):
    """
    Prepara opciones de codificación tomando como referencia el video fuente.
    """
    codec_fuente = datos_video["codec"]
    encoder = ENCODERS.get(codec_fuente, "libx264")

    opciones = {
        "vcodec": encoder,
        "pix_fmt": datos_video["pixel_format"],
        "t": datos_video["duration"],
        "movflags": "+faststart",
        "map_metadata": 0,
    }

    if datos_video["fps"]:
        opciones["r"] = datos_video["fps"]

    bitrate = datos_video["bitrate"]

    if bitrate and bitrate not in {"N/A", "0"}:
        opciones["video_bitrate"] = int(bitrate)
    else:
        # Usar calidad alta si FFprobe no entrega bitrate del stream.
        opciones["crf"] = int(config.get("crf", 18))

    if datos_video["has_audio"]:
        opciones["acodec"] = "aac"
        opciones["audio_bitrate"] = "192k"

    return opciones



def _calcular_posicion_texto(
    position,
    video_w,
    video_h,
    texto_w,
    texto_h,
    margin,
):
    """Calcula la esquina superior izquierda de la capa de texto."""
    margen_x = int(video_w * margin)
    margen_y = int(video_h * margin)

    # Una lista de JSON como ["center", "bottom"] se convierte en tupla.
    if isinstance(position, list):
        position = tuple(position)

    if isinstance(position, tuple) and len(position) == 2:
        horizontal, vertical = position

        if horizontal == "left":
            x = margen_x
        elif horizontal == "right":
            x = video_w - texto_w - margen_x
        else:
            x = (video_w - texto_w) // 2

        if vertical == "top":
            y = margen_y
        elif vertical == "center":
            y = (video_h - texto_h) // 2
        else:
            y = video_h - texto_h - margen_y

        return x, y

    # También permite posiciones numéricas [x, y].
    return int(position[0]), int(position[1])


def agregar_texto(config):
    """
    Agrega las capas indicadas en config["textos"] al video config["video"].
    """
    video_path = str(config["video"])
    ruta_salida = Path(config["output"])
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Leer una vez los metadatos para usar las dimensiones y la codificación
    # del video original.
    datos_video = _leer_datos_video(video_path)

    entrada_video = ffmpeg.input(video_path)

    # Los PNG temporales deben seguir existiendo hasta que FFmpeg termine.
    with tempfile.TemporaryDirectory() as temp_dir:
        # Si no se pasan dimensiones, conservar las dimensiones de presentación
        # del video fuente.
        ancho_salida = int(
            config.get("target_width", datos_video["width"])
        )
        alto_salida = int(
            config.get("target_height", datos_video["height"])
        )

        # "pad" conserva el cuadro completo y añade bordes si hacen falta.
        # "crop" llena el lienzo y recorta el sobrante.
        modo_ajuste = config.get("fit_mode", "pad")

        video_ajustado = ajustar_video_a_lienzo(
            video=entrada_video.video,
            target_width=ancho_salida,
            target_height=alto_salida,
            mode=modo_ajuste,
            crop_offset_pct=float(config.get("crop_offset_pct", 0)),
            pad_color=config.get("pad_color", "black"),
        )

        # El tamaño de texto, sus márgenes y sus posiciones deben calcularse
        # con las dimensiones del cuadro que se generará.
        datos_video_salida = {
            **datos_video,
            "width": ancho_salida,
            "height": alto_salida,
        }

        video_con_textos = _crear_capas_texto(
            video_stream=video_ajustado,
            textos=config["textos"],
            datos_video=datos_video_salida,
            temp_dir=temp_dir,
        )

        opciones_salida = _crear_opciones_salida(config, datos_video)
        streams_salida = [video_con_textos]

        if datos_video["has_audio"]:
            streams_salida.append(entrada_video.audio)

        resultado = ffmpeg.output(
            *streams_salida,
            str(ruta_salida),
            **opciones_salida,
        )

        resultado.overwrite_output().run()

    print(f"Video generado: {ruta_salida}")
    return str(ruta_salida)

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