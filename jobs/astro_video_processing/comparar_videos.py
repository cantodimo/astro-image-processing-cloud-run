import argparse
import json
from pathlib import Path

import ffmpeg


def leer_datos_video(video_path):
    """Obtiene dimensiones visibles y duración de un video."""
    metadata = ffmpeg.probe(video_path)

    video_metadata = next(
        stream
        for stream in metadata["streams"]
        if stream["codec_type"] == "video"
    )

    ancho = int(video_metadata["width"])
    alto = int(video_metadata["height"])

    # Un video de teléfono puede almacenar los cuadros girados y usar
    # metadatos para indicar la orientación de reproducción.
    rotacion = video_metadata.get("tags", {}).get("rotate", 0)

    for dato in video_metadata.get("side_data_list", []):
        if "rotation" in dato:
            rotacion = dato["rotation"]
            break

    rotacion = round(float(rotacion)) % 360

    if rotacion in {90, 270}:
        ancho, alto = alto, ancho

    tiene_audio = any(
        stream.get("codec_type") == "audio"
        for stream in metadata["streams"]
    )

    return {
        "width": ancho,
        "height": alto,
        "has_audio": tiene_audio,
        "duration": float(metadata["format"]["duration"]),
    }


def recortar_seccion_vertical(
    video,
    width,
    height,
    start_pct,
    end_pct,
):
    """
    Recorta toda la anchura del video y conserva el tramo vertical indicado.
    """
    top = round(height * start_pct / 100)
    bottom = round(height * end_pct / 100)

    # Mantener el recorte dentro de los límites del cuadro.
    top = min(height - 1, top)
    bottom = max(top + 1, min(height, bottom))

    crop_height = bottom - top

    return video.filter(
        "crop",
        width,
        crop_height,
        0,
        top,
    )


def preparar_video(
    video_path,
    datos_video,
    start_pct,
    end_pct,
    target_width,
    fps,
):
    """
    Recorta una sección, la escala proporcionalmente y normaliza FPS y formato.
    """
    entrada = ffmpeg.input(video_path)

    video = recortar_seccion_vertical(
        video=entrada.video,
        width=datos_video["width"],
        height=datos_video["height"],
        start_pct=start_pct,
        end_pct=end_pct,
    )

    # -2 conserva la proporción y calcula una altura par para yuv420p.
    video = video.filter(
        "scale",
        target_width,
        -2,
        flags="lanczos",
    )

    # Normalizar ambos clips para que vstack pueda combinarlos.
    video = (
        video
        .filter("setsar", 1)
        .filter("fps", fps=fps)
        .filter("setpts", "PTS-STARTPTS")
        .filter("format", "yuv420p")
    )

    return video, entrada


def comparar_videos(config):
    """
    Recorta dos videos, iguala sus anchos sin deformarlos y los apila.

    Claves requeridas:
        top_video_path
        bottom_video_path
        output

    Claves opcionales:
        top_start_pct       (predeterminado: 0)
        top_end_pct         (predeterminado: 100)
        bottom_start_pct    (predeterminado: 0)
        bottom_end_pct      (predeterminado: 100)
        fps                 (predeterminado: 24)
        crf                 (predeterminado: 18)
        preset              (predeterminado: "medium")
    """
    top_video_path = str(config["top_video_path"])
    bottom_video_path = str(config["bottom_video_path"])
    output_path = Path(config["output"])

    top_start_pct = float(config.get("top_start_pct", 0))
    top_end_pct = float(config.get("top_end_pct", 100))
    bottom_start_pct = float(config.get("bottom_start_pct", 0))
    bottom_end_pct = float(config.get("bottom_end_pct", 100))

    fps = int(config.get("fps", 24))

    # Consultar cada video para calcular su recorte y el tamaño común.
    top_data = leer_datos_video(top_video_path)
    bottom_data = leer_datos_video(bottom_video_path)

    top_crop_width = top_data["width"]
    bottom_crop_width = bottom_data["width"]

    # La imagen de comparación usa como ancho el recorte más ancho.
    target_width = max(top_crop_width, bottom_crop_width)

    # H.264 con yuv420p requiere dimensiones pares.
    target_width += target_width % 2

    # Ambas partes se muestran simultáneamente; termina la más corta.
    output_duration = min(
        top_data["duration"],
        bottom_data["duration"],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    video_top, entrada_top = preparar_video(
        video_path=top_video_path,
        datos_video=top_data,
        start_pct=top_start_pct,
        end_pct=top_end_pct,
        target_width=target_width,
        fps=fps,
    )

    video_bottom, entrada_bottom = preparar_video(
        video_path=bottom_video_path,
        datos_video=bottom_data,
        start_pct=bottom_start_pct,
        end_pct=bottom_end_pct,
        target_width=target_width,
        fps=fps,
    )

    # Apilar los videos: uno arriba y el otro abajo.
    video_combinado = ffmpeg.filter(
        [video_top, video_bottom],
        "vstack",
        inputs=2,
    )

    audio_mode = config.get("audio_mode", "none")

    audio_top_available = top_data["has_audio"]
    audio_bottom_available = bottom_data["has_audio"]

    streams_salida = [video_combinado]

    def preparar_audio(audio_stream):
        """Alinea el audio al inicio y lo limita a la duración de salida."""
        return (
            audio_stream
            .filter("atrim", duration=output_duration)
            .filter("asetpts", "PTS-STARTPTS")
        )

    if audio_mode == "top" and audio_top_available:
        streams_salida.append(
            preparar_audio(entrada_top.audio)
        )

    elif audio_mode == "bottom" and audio_bottom_available:
        streams_salida.append(
            preparar_audio(entrada_bottom.audio)
        )

    elif audio_mode == "both":
        audios = []

        if audio_top_available:
            audios.append(preparar_audio(entrada_top.audio))

        if audio_bottom_available:
            audios.append(preparar_audio(entrada_bottom.audio))

        if len(audios) == 1:
            # Si solo un video tiene audio, conservar esa pista.
            streams_salida.append(audios[0])

        elif len(audios) == 2:
            # Mezclar las dos pistas en una sola.
            audio_mezclado = ffmpeg.filter(
                audios,
                "amix",
                inputs=2,
                duration="shortest",
                dropout_transition=0,
            )
            streams_salida.append(audio_mezclado)

    opciones_salida = {
        "vcodec": "libx264",
        "pix_fmt": "yuv420p",
        "crf": int(config.get("crf", 18)),
        "preset": config.get("preset", "medium"),
        "r": fps,
        "t": output_duration,
        "movflags": "+faststart",
    }

    if len(streams_salida) > 1:
        opciones_salida["acodec"] = "aac"
        opciones_salida["audio_bitrate"] = "192k"

    resultado = ffmpeg.output(
        *streams_salida,
        str(output_path),
        **opciones_salida,
    )

    resultado.overwrite_output().run()

    print(f"Video superior: {top_video_path}")
    print(f"Video inferior: {bottom_video_path}")
    print(f"Ancho de salida: {target_width}")
    print(f"Duración de salida: {output_duration:.2f} segundos")
    print(f"Video generado: {output_path}")

    return str(output_path)


def leer_argumentos():
    parser = argparse.ArgumentParser(
        description=(
            "Recorta dos videos, ajusta sus anchos sin deformarlos "
            "y los apila en una comparación."
        )
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
    args = leer_argumentos()

    if args.config_json:
        with open(args.config_json, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)
    else:
        config = json.loads(args.config)

    comparar_videos(config)


if __name__ == "__main__":
    ejecutar()