FROM alpine:3.22

RUN apk add --no-cache ffmpeg jq

WORKDIR /app

COPY agregar_logo_a_video.sh /app/agregar_logo_a_video.sh
COPY main.sh /app/main.sh

RUN chmod +x /app/agregar_logo_a_video.sh /app/main.sh

ENTRYPOINT ["/app/main.sh"]