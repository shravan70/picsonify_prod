FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# HuggingFace cache location
ENV HF_HOME=/app/hf_cache
ENV TRANSFORMERS_CACHE=/app/hf_cache

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 Pre-download model (NO INDENTATION!)
RUN python - <<EOF
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer

VisionEncoderDecoderModel.from_pretrained(
    "nlpconnect/vit-gpt2-image-captioning",
    cache_dir="/app/hf_cache"
)
ViTImageProcessor.from_pretrained(
    "nlpconnect/vit-gpt2-image-captioning",
    cache_dir="/app/hf_cache"
)
AutoTokenizer.from_pretrained(
    "nlpconnect/vit-gpt2-image-captioning",
    cache_dir="/app/hf_cache"
)
EOF

# Copy app code
COPY . .

EXPOSE 8080

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "300", \
     "--workers", "1", \
     "--threads", "4", \
     "app:app"]
