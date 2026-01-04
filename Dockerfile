# -------------------------
# Base image
# -------------------------
FROM python:3.10-slim

WORKDIR /app

# -------------------------
# Environment variables
# -------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    HF_HOME=/tmp/hf_cache \
    TRANSFORMERS_CACHE=/tmp/hf_cache

# -------------------------
# System dependencies
# -------------------------
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# Install Python dependencies
# -------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# -------------------------
# Create writable cache dirs
# -------------------------
RUN mkdir -p /tmp/hf_cache /tmp/images /tmp/audio

# -------------------------
# Pre-download HuggingFace model (build-time)
# -------------------------
RUN python - <<EOF
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
EOF

# -------------------------
# Copy application code
# -------------------------
COPY . .

# -------------------------
# Expose port
# -------------------------
EXPOSE 8080

# -------------------------
# Run app (Gunicorn)
# -------------------------
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "300", \
     "app:app"]
