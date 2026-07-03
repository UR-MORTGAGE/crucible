# Crucible API container (talks to a vLLM/ROCm server for the local lane).
# The heavy vLLM+ROCm image is a separate service — see docker-compose.yml.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data ./data
COPY ui ./ui

EXPOSE 8080
CMD ["uvicorn", "crucible.server:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8080"]
