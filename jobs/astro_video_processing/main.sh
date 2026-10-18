#!/bin/sh
set -eu

CONFIG_FILE="$1"
TASK_INDEX="$CLOUD_RUN_TASK_INDEX"

PROCESS_SCRIPT="$(dirname "$0")/agregar_logo_a_video.sh"

CONFIG="$(jq -c ".tasks[$TASK_INDEX]" "$CONFIG_FILE")"

VIDEO="$(printf '%s' "$CONFIG" | jq -r '.video')"
LOGO="$(printf '%s' "$CONFIG" | jq -r '.logo')"
OUTPUT="$(printf '%s' "$CONFIG" | jq -r '.output')"

TARGET_WIDTH="$(printf '%s' "$CONFIG" | jq -r '.target_width')"
TARGET_HEIGHT="$(printf '%s' "$CONFIG" | jq -r '.target_height')"
SCALE="$(printf '%s' "$CONFIG" | jq -r '.scale')"
OPACITY="$(printf '%s' "$CONFIG" | jq -r '.opacity')"
MARGIN="$(printf '%s' "$CONFIG" | jq -r '.margin')"
FPS="$(printf '%s' "$CONFIG" | jq -r '.fps')"
POSITION="$(printf '%s' "$CONFIG" | jq -r '.position')"
KEY_COLOR="$(printf '%s' "$CONFIG" | jq -r '.key_color // empty')"

if [ -n "$KEY_COLOR" ]; then
    sh "$PROCESS_SCRIPT" \
        "$VIDEO" "$LOGO" "$OUTPUT" \
        "$TARGET_WIDTH" "$TARGET_HEIGHT" "$SCALE" \
        "$OPACITY" "$MARGIN" "$FPS" "$POSITION" "$KEY_COLOR"
else
    sh "$PROCESS_SCRIPT" \
        "$VIDEO" "$LOGO" "$OUTPUT" \
        "$TARGET_WIDTH" "$TARGET_HEIGHT" "$SCALE" \
        "$OPACITY" "$MARGIN" "$FPS" "$POSITION"
fi