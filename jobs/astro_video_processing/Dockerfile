FROM alpine:3.22

RUN apk add --no-cache ffmpeg

WORKDIR /app

COPY agregar_logo_a_video.sh /app/agregar_logo_a_video.sh
RUN chmod +x /app/agregar_logo_a_video.sh

ENTRYPOINT ["/app/agregar_logo_a_video.sh"]