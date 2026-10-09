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

ffmpeg -nostdin -hide_banner -loglevel warning -stats -y \
    -i "$VIDEO" \
    -loop 1 -i "$LOGO" \
    -filter_complex "$FILTER_COMPLEX" \
    -map "[outv]" \
    -map "0:a?" \
    -c:v libx264 \
    -preset medium \
    -crf 0 \
    -pix_fmt yuv420p \
    -r "$FPS" \
    -c:a aac \
    -movflags +faststart \
    "$OUTPUT"

echo "Video generado: $OUTPUT"