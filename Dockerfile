FROM python:3.11-slim

LABEL maintainer="Bilingual Ebook Maker"
LABEL description="Translate ebooks and create bilingual EPUB with IELTS vocabulary highlights"

# Install system dependencies including Calibre for ebook conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    calibre \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories for uploads and outputs
RUN mkdir -p /app/uploads /app/outputs

# Set environment variables
ENV UPLOAD_DIR=/app/uploads
ENV OUTPUT_DIR=/app/outputs
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

VOLUME ["/app/uploads", "/app/outputs"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
