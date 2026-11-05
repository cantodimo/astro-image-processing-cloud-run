import argparse
import json
import time
from pathlib import Path

import ffmpeg

from helpers.reescalar import ajustar_video_a_lienzo


def cargar_elementos(elementos_config):
    """
    Carga la lista de elementos desde:
    - Una lista de diccionarios que ya está en memoria.
    - La ruta a un archivo JSON.
    - Una cadena que contiene el JSON.
    """
    if isinstance(elementos_config, list):
        return elementos_config

    posible_ruta = Path(elementos_config)

    if posible_ruta.is_file():
        with posible_ruta.open("r", encoding="utf-8") as archivo:
            return json.load(archivo)

    return json.loads(elementos_config)


def elegir_lienzo(elementos):
    # Consultar las dimensiones de cada imagen o video con FFprobe.
    dimensiones = []

    for elemento in elementos:
        metadatos = ffmpeg.probe(elemento["path"])

        stream_video = next(
            stream
            for stream in metadatos["streams"]
            if stream["codec_type"] == "video"
        )

        ancho = int(stream_video["width"])
        alto = int(stream_video["height"])

        dimensiones.append({
            "width": ancho,
            "height": alto,
            "area": ancho * alto,
        })

    # El elemento con mayor área define el tamaño del lienzo.
    elemento_mayor = max(
        dimensiones,
        key=lambda elemento: elemento["area"],
    )

    ancho_lienzo = elemento_mayor["width"]
    alto_lienzo = elemento_mayor["height"]

    # H.264 con yuv420p requiere dimensiones pares.
    ancho_lienzo += ancho_lienzo % 2
    alto_lienzo += alto_lienzo % 2

    return ancho_lienzo, alto_lienzo


def detectar_configuracion_video(elementos, fps_salida):
    # Usar el primer video como referencia para encoder, formato y bitrate.
    videos = [
        elemento
        for elemento in elementos
        if elemento["type"] == "video"
    ]

    # Si solo hay imágenes, usar H.264.
    if not videos:
        return {
            "vcodec": "libx264",
            "pix_fmt": "yuv420p",
            "fps": fps_salida,
        }

    metadatos = ffmpeg.probe(videos[0]["path"])

    stream = next(
        stream
        for stream in metadatos["streams"]
        if stream["codec_type"] == "video"
    )

    encoders = {
        "h264": "libx264",
        "hevc": "libx265",
        "vp9": "libvpx-vp9",
        "av1": "libaom-av1",
        "mpeg4": "mpeg4",
    }

    codec = stream.get("codec_name")

    opciones = {
        "vcodec": encoders.get(codec, "libx264"),
        "pix_fmt": stream.get("pix_fmt", "yuv420p"),
        "fps": fps_salida,
    }

    bitrate = stream.get("bit_rate")

    if bitrate and bitrate not in {"N/A", "0"}:
        opciones["video_bitrate"] = int(bitrate)

    return opciones

def crear_video(
    elementos,
    audio=None,
    inicio_audio=0,
    salida=None,
    fps=24,
    target_width=None,
    target_height=None,
    fit_mode="pad",
    crop_offset_pct=0,
    pad_color="black",
):
    # Acepta elementos como lista, ruta a JSON o cadena JSON.
    elementos = cargar_elementos(elementos)

    ancho, alto = elegir_lienzo(elementos)

    # La duración total sigue siendo la suma de duration de cada elemento.
    duracion_total = sum(
        float(elemento["duration"])
        for elemento in elementos
    )

    if salida is None:
        ruta_salida = (
            Path.cwd()
            / "salida_procesos"
            / f"video_concatenado_{int(time.time())}.mp4"
        )
    else:
        ruta_salida = Path(salida)

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    clips_video = []

    for elemento in elementos:
        duracion = float(elemento["duration"])

        if elemento["type"] == "image":
            # La imagen conserva el comportamiento anterior:
            # se repite desde el inicio durante duration segundos.
            entrada = ffmpeg.input(
                elemento["path"],
                loop=1,
                framerate=fps,
            )

            clip = entrada.video.filter(
                "trim",
                duration=duracion,
            )

        else:
            entrada = ffmpeg.input(elemento["path"])

            # Si no se especifica seg_inicio_video, el segmento empieza en 0.
            inicio_video = float(
                elemento.get("seg_inicio_video", 0)
            )

            # duration indica cuánto dura el segmento desde inicio_video.
            clip = entrada.video.filter(
                "trim",
                start=inicio_video,
                duration=duracion,
            )

        # Reiniciar los tiempos del segmento y aplicar los filtros
        # que se usan tanto para imágenes como para videos.
        clip = (
            clip
            .filter("setpts", "PTS-STARTPTS")
            .filter("fps", fps=fps)
            .filter(
                "scale",
                ancho,
                alto,
                force_original_aspect_ratio="decrease",
            )
            .filter(
                "pad",
                ancho,
                alto,
                "(ow-iw)/2",
                "(oh-ih)/2",
                color="black",
            )
            .filter("setsar", 1)
            .filter("format", "yuv420p")
        )

        clips_video.append(clip)

    # Si hay un solo elemento, usarlo directamente.
    # Si hay varios, concatenarlos conservando el orden de la lista.
    if len(clips_video) == 1:
        video_final = clips_video[0]
    else:
        video_final = ffmpeg.concat(
            *clips_video,
            v=1,
            a=0,
        ).node[0]

    tiene_ancho_objetivo = target_width is not None
    tiene_alto_objetivo = target_height is not None

    if tiene_ancho_objetivo != tiene_alto_objetivo:
        raise ValueError(
            "Debes especificar juntos target_width y target_height."
        )

    if tiene_ancho_objetivo:
        video_final = ajustar_video_a_lienzo(
            video=video_final,
            target_width=target_width,
            target_height=target_height,
            mode=fit_mode,
            crop_offset_pct=crop_offset_pct,
            pad_color=pad_color,
        )

    opciones_video = detectar_configuracion_video(elementos, fps)

    # Opciones comunes para el archivo final.
    opciones_salida = {
        "vcodec": opciones_video["vcodec"],
        "pix_fmt": opciones_video["pix_fmt"],
        "r": opciones_video["fps"],
        "t": duracion_total,
        "movflags": "+faststart",
    }

    # Solo pasar bitrate cuando FFprobe encontró uno.
    # Esto evita enviar "-b:v None" cuando solo hay imágenes.
    if opciones_video.get("video_bitrate") is not None:
        opciones_salida["video_bitrate"] = opciones_video["video_bitrate"]

    streams_salida = [video_final]

    # El audio sigue siendo opcional.
    if audio:
        audio_entrada = ffmpeg.input(audio).audio

        audio_final = (
            audio_entrada
            .filter(
                "atrim",
                start=inicio_audio,
                duration=duracion_total,
            )
            .filter("asetpts", "PTS-STARTPTS")
            .filter("apad")
            .filter("atrim", duration=duracion_total)
        )

        streams_salida.append(audio_final)

        opciones_salida["acodec"] = "aac"
        opciones_salida["audio_bitrate"] = "192k"

    resultado = ffmpeg.output(
        *streams_salida,
        str(ruta_salida),
        **opciones_salida,
    )

    resultado.overwrite_output().run()

    print(f"Video creado: {ruta_salida}")

if __name__ == "__main__":
    # argparse obtiene los valores para la ejecución independiente.
    parser = argparse.ArgumentParser(
        description="Une imágenes y videos y les agrega audio."
    )

    parser.add_argument(
        "--elementos",
        required=True,
        help="Ruta al JSON o lista de elementos escrita como texto JSON.",
    )
    parser.add_argument(
        "--audio",
        default=None,
        help="Ruta al archivo de audio.",
    )
    parser.add_argument(
        "--inicio-audio",
        type=float,
        default=0,
        help="Segundo donde comienza el audio. Predeterminado: 0.",
    )
    parser.add_argument(
        "--salida",
        default=None,
        help="Ruta del MP4 de salida.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=24,
        help="FPS de salida. Predeterminado: 24.",
    )

    parser.add_argument("--target-width", type=int, default=None)
    parser.add_argument("--target-height", type=int, default=None)
    parser.add_argument(
        "--fit-mode",
        choices=["crop", "pad"],
        default="pad",
    )
    parser.add_argument(
        "--crop-offset-pct",
        type=float,
        default=0,
    )
    parser.add_argument(
        "--pad-color",
        default="black",
    )

    args = parser.parse_args()

    crear_video(
        elementos=args.elementos,
        audio=args.audio,
        inicio_audio=args.inicio_audio,
        salida=args.salida,
        fps=args.fps,
        target_width=args.target_width,
        target_height=args.target_height,
        fit_mode=args.fit_mode,
        crop_offset_pct=args.crop_offset_pct,
        pad_color=args.pad_color
    )