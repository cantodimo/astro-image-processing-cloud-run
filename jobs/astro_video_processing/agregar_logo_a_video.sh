#!/bin/sh
set -eu

# Uso:
# ./agregar_logo_a_video.sh VIDEO LOGO SALIDA TARGET_WIDTH TARGET_HEIGHT SCALE OPACITY MARGIN FPS POSITION [KEY_COLOR]

# Verificar que se reciban los 10 parámetros obligatorios y uno opcional.
if [ "$#" -lt 10 ] || [ "$#" -gt 11 ]; then
    echo "Uso: $0 VIDEO LOGO SALIDA TARGET_WIDTH TARGET_HEIGHT SCALE OPACITY MARGIN FPS POSITION [KEY_COLOR]" >&2
    exit 1
fi

# Rutas de entrada y salida.
VIDEO="$1"
LOGO="$2"
OUTPUT="$3"

# Configuración del video y del logo.
TARGET_WIDTH="$4"   # Ancho final del video en píxeles.
TARGET_HEIGHT="$5"  # Alto final del video en píxeles.
SCALE="$6"          # Ancho del logo como proporción del ancho del video.
OPACITY="$7"        # Opacidad del logo: 0 (transparente) a 1 (opaco).
MARGIN="$8"         # Margen respecto a los bordes, como proporción.
FPS="$9"            # Fotogramas por segundo del video de salida.
POSITION="${10}"     # Posición horizontal del logo: right o left.
KEY_COLOR="${11:-}"  # Color de fondo que se eliminará; vacío para no eliminarlo.

# Calcular el ancho del logo y los márgenes en píxeles.
LOGO_WIDTH=$(awk "BEGIN {printf \"%d\", $TARGET_WIDTH * $SCALE}")
MARGIN_X=$(awk "BEGIN {printf \"%d\", $TARGET_WIDTH * $MARGIN}")
MARGIN_Y=$(awk "BEGIN {printf \"%d\", $TARGET_HEIGHT * $MARGIN}")

# Calcular la posición horizontal del logo según la configuración.
case "$POSITION" in
    right) X="W-w-${MARGIN_X}" ;;
    left)  X="${MARGIN_X}" ;;
    *)
        echo "POSITION debe ser right o left" >&2
        exit 1
        ;;
esac

Y="H-h-${MARGIN_Y}"

# Escalar el logo conservando su proporción y canal alfa.
LOGO_FILTER="[1:v]scale=${LOGO_WIDTH}:-1,format=rgba"

# Si se especificó un color, eliminarlo del fondo del logo.
if [ -n "$KEY_COLOR" ]; then
    LOGO_FILTER="${LOGO_FILTER},colorkey=${KEY_COLOR}:0.235:0"
fi

LOGO_FILTER="${LOGO_FILTER},colorchannelmixer=aa=${OPACITY}[logo]"

FILTER_COMPLEX="[0:v]scale=${TARGET_WIDTH}:${TARGET_HEIGHT},setsar=1[video];${LOGO_FILTER};[video][logo]overlay=x=${X}:y=${Y}:shortest=1:format=auto[outv]"

echo "Procesando video..."

# Inspeccionar el primer flujo de video.
SOURCE_INFO=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,profile,pix_fmt,level,bit_rate,avg_frame_rate,r_frame_rate \
    -of default=noprint_wrappers=1 "$VIDEO")

SOURCE_CODEC=$(printf '%s\n' "$SOURCE_INFO" |
    sed -n 's/^codec_name=//p')
SOURCE_PROFILE=$(printf '%s\n' "$SOURCE_INFO" |
    sed -n 's/^profile=//p')
SOURCE_PIX_FMT=$(printf '%s\n' "$SOURCE_INFO" |
    sed -n 's/^pix_fmt=//p')
SOURCE_LEVEL=$(printf '%s\n' "$SOURCE_INFO" |
    sed -n 's/^level=//p')
SOURCE_BITRATE=$(printf '%s\n' "$SOURCE_INFO" |
    sed -n 's/^bit_rate=//p')
SOURCE_AVG_FPS=$(printf '%s\n' "$SOURCE_INFO" |
    sed -n 's/^avg_frame_rate=//p')
SOURCE_R_FPS=$(printf '%s\n' "$SOURCE_INFO" |
    sed -n 's/^r_frame_rate=//p')

# Preferir el FPS promedio. Si no está disponible, usar el FPS nominal.
SOURCE_FPS="$SOURCE_AVG_FPS"
case "$SOURCE_FPS" in
    ''|N/A|0/0)
        SOURCE_FPS="$SOURCE_R_FPS"
        ;;
esac

case "$SOURCE_FPS" in
    ''|N/A|0/0)
        echo "Error: ffprobe no pudo determinar el FPS del video." >&2
        exit 1
        ;;
esac

echo "Datos detectados por ffprobe:"
echo "  Códec:          ${SOURCE_CODEC:-no informado}"
echo "  Perfil:         ${SOURCE_PROFILE:-no informado}"
echo "  Formato píxel:  ${SOURCE_PIX_FMT:-no informado}"
echo "  Nivel:          ${SOURCE_LEVEL:-no informado}"
echo "  Bitrate video:  ${SOURCE_BITRATE:-no informado}"
echo "  FPS promedio:   ${SOURCE_AVG_FPS:-no informado}"
echo "  FPS nominal:    ${SOURCE_R_FPS:-no informado}"
echo "  FPS de salida:  $SOURCE_FPS"

# Elegir un encoder FFmpeg según el códec detectado.
case "$SOURCE_CODEC" in
    h264)  VIDEO_ENCODER="libx264" ;;
    hevc)  VIDEO_ENCODER="libx265" ;;
    vp9)   VIDEO_ENCODER="libvpx-vp9" ;;
    av1)   VIDEO_ENCODER="libaom-av1" ;;
    mpeg4) VIDEO_ENCODER="mpeg4" ;;
    *)
        echo "Códec de entrada no contemplado: $SOURCE_CODEC" >&2
        exit 1
        ;;
esac

# Usar el bitrate de origen como objetivo si ffprobe informó uno válido.
BITRATE_ARGS=""
case "$SOURCE_BITRATE" in
    ''|N/A|0) ;;
    *) BITRATE_ARGS="-b:v $SOURCE_BITRATE" ;;
esac

ffmpeg -nostdin -hide_banner -loglevel warning -stats -y \
    -i "$VIDEO" \
    -loop 1 -i "$LOGO" \
    -filter_complex "$FILTER_COMPLEX" \
    -map "[outv]" \
    -map "0:a?" \
    -map_metadata 0 \
    -c:v "$VIDEO_ENCODER" \
    $BITRATE_ARGS \
    -pix_fmt "$SOURCE_PIX_FMT" \
    -r "$SOURCE_FPS" \
    -c:a aac \
    -b:a 192k \
    -movflags +faststart \
    "$OUTPUT"

echo "Video generado: $OUTPUT"