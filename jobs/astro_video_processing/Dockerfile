FROM python:3.12-alpine

RUN apk add --no-cache ffmpeg

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#hace que Python envíe su salida (print y logs) sin esperar a llenar un búfer.
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "/app/main.py"]