#FROM python:3.12-slim-bookworm
FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY py_processing ./py_processing

CMD ["python", "app.py"]