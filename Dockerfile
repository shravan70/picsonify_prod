# Base image
FROM python:3.10-slim

# Working directory
WORKDIR /app

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# HuggingFace cache directory (writable)
RUN mkdir -p /app/hf_cache
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache

# Pre-download model (prevents runtime permission errors)
RUN python - <<EOF
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
EOF

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "300", "--workers", "1", "--threads", "4", "app:app"]
