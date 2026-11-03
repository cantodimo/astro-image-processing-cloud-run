from fractions import Fraction

import ffmpeg


ENCODERS = {
    "h264": "libx264",
    "hevc": "libx265",
    "vp9": "libvpx-vp9",
    "av1": "libaom-av1",
    "mpeg4": "mpeg4",
}


def agregar_logo(config):
    video = config["video"]
    logo = config["logo"]
    salida = config["output"]

    ancho_salida = int(config["target_width"])
    alto_salida = int(config["target_height"])
    escala_logo = float(config["scale"])
    opacidad = float(config["opacity"])
    margen = float(config["margin"])
    posicion = config["position"]
    key_color = config.get("key_color")

    # El script shell calcula estos valores truncando a entero.
    ancho_logo = int(ancho_salida * escala_logo)
    margen_x = int(ancho_salida * margen)
    margen_y = int(alto_salida * margen)

    if posicion == "right":
        x_logo = f"W-w-{margen_x}"
    else:
        x_logo = str(margen_x)

    y_logo = f"H-h-{margen_y}"

    # Inspeccionar los streams del video fuente, como hacía ffprobe en Bash.
    metadatos = ffmpeg.probe(
        video,
        select_streams="v:0",
        show_entries=(
            "stream=codec_type,codec_name,profile,pix_fmt,level,bit_rate,"
            "avg_frame_rate,r_frame_rate"
        ),
    )

    stream = next(
        stream
        for stream in metadatos["streams"]
        if stream["codec_type"] == "video"
    )

    codec_fuente = stream.get("codec_name")
    encoder = ENCODERS[codec_fuente]

    formato_pixel = stream.get("pix_fmt")
    bitrate = stream.get("bit_rate")

    fps_promedio = stream.get("avg_frame_rate")
    fps_nominal = stream.get("r_frame_rate")

    # Preferir FPS promedio; si falta, usar FPS nominal.
    fps_salida = fps_promedio
    if not fps_salida or fps_salida in {"N/A", "0/0"}:
        fps_salida = fps_nominal

    # Parsear y volver a emitir la fracción para normalizarla.
    fps_salida = str(Fraction(fps_salida))

    entrada_video = ffmpeg.input(video)
    entrada_logo = ffmpeg.input(logo, loop=1)

    # Ajustar el video al tamaño configurado. Esto conserva el comportamiento
    # del shell: el video se escala directamente a esas dimensiones.
    video_filtrado = (
        entrada_video.video
        .filter("scale", ancho_salida, alto_salida)
        .filter("setsar", 1)
    )

    # Escalar el logo conservando su proporción y habilitar alfa.
    logo_filtrado = (
        entrada_logo.video
        .filter("scale", ancho_logo, -1)
        .filter("format", "rgba")
    )

    # El shell usa tolerancia fija 0.235 cuando se da key_color.
    if key_color:
        logo_filtrado = logo_filtrado.filter(
            "colorkey",
            key_color,
            0.235,
            0,
        )

    logo_filtrado = logo_filtrado.filter(
        "colorchannelmixer",
        aa=opacidad,
    )

    video_con_logo = ffmpeg.overlay(
        video_filtrado,
        logo_filtrado,
        x=x_logo,
        y=y_logo,
        shortest=1,
        format="auto",
    )

    # El shell conserva el stream de audio si existe, pero no falla si no hay.
    tiene_audio = any(
        stream.get("codec_type") == "audio"
        for stream in ffmpeg.probe(video)["streams"]
    )

    opciones_salida = {
        "vcodec": encoder,
        "pix_fmt": formato_pixel,
        "r": fps_salida,
        "acodec": "aac",
        "audio_bitrate": "192k",
        "movflags": "+faststart",
        "map_metadata": 0,
        "loglevel": "warning",
        "stats": None,
    }

    # Solo usar bitrate si FFprobe lo informó con un valor válido.
    if bitrate and bitrate not in {"N/A", "0"}:
        opciones_salida["video_bitrate"] = int(bitrate)

    if tiene_audio:
        resultado = ffmpeg.output(
            video_con_logo,
            entrada_video.audio,
            salida,
            **opciones_salida,
        )
    else:
        resultado = ffmpeg.output(
            video_con_logo,
            salida,
            **opciones_salida,
        )

    resultado.overwrite_output().run()
    print(f"Video generado: {salida}")