def ajustar_video_a_lienzo(
    video,
    target_width,
    target_height,
    mode="pad",
    crop_offset_pct=0,
    pad_color="black",
):
    """
    Ajusta un stream de video a un lienzo de tamaño fijo sin deformarlo.

    mode="crop":
        Escala hasta cubrir el lienzo y recorta el sobrante.
        crop_offset_pct mueve el recorte entre -100 y 100:
            -100 = izquierda o arriba
               0 = centrado
             100 = derecha o abajo

    mode="pad":
        Escala para que el video quepa completo y rellena el espacio restante.

    Devuelve un stream de video de target_width x target_height.
    """
    ancho = int(target_width)
    alto = int(target_height)

    if mode == "crop":
        # Escalar hasta que el video cubra todo el lienzo.
        video = video.filter(
            "scale",
            ancho,
            alto,
            force_original_aspect_ratio="increase",
            flags="lanczos",
        )

        # Convertir el desplazamiento porcentual a un valor entre -1 y 1.
        desplazamiento = float(crop_offset_pct) / 100

        # -100 elige el inicio del sobrante, 0 su centro y 100 su final.
        posicion_x = (
            f"trunc((iw-ow)*(0.5+({desplazamiento})/2))"
        )
        posicion_y = (
            f"trunc((ih-oh)*(0.5+({desplazamiento})/2))"
        )

        video = video.filter(
            "crop",
            ancho,
            alto,
            posicion_x,
            posicion_y,
        )

    elif mode == "pad":
        # Escalar para que todo el video quepa dentro del lienzo.
        video = video.filter(
            "scale",
            ancho,
            alto,
            force_original_aspect_ratio="decrease",
            flags="lanczos",
        )

        # Centrarlo y rellenar los bordes con el color indicado.
        video = video.filter(
            "pad",
            ancho,
            alto,
            "(ow-iw)/2",
            "(oh-ih)/2",
            color=pad_color,
        )

    else:
        raise ValueError("mode debe ser 'crop' o 'pad'")

    # Normalizar la relación de aspecto de los píxeles.
    return video.filter("setsar", 1)