FROM python:3.12-alpine

RUN apk add --no-cache ffmpeg

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY agregar_logo_a_video.py .
COPY unir_imagenes_videos_audios.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "/app/main.py"]