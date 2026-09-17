FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PADDLE_PDX_CACHE_HOME=/models/paddlex \
    HF_HOME=/models/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY ui ./ui
RUN pip install --no-cache-dir '.[paddle,table-fallbacks]'

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data /models /app/runtime \
    && chown -R appuser:appuser /data /models /app/runtime
USER appuser

EXPOSE 8000
CMD ["uvicorn", "pdf_extraction.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
