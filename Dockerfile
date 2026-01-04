# Base image
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download transformers model
RUN python -c "from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer; \
    VisionEncoderDecoderModel.from_pretrained('nlpconnect/vit-gpt2-image-captioning', cache_dir='/app/hf_cache'); \
    ViTImageProcessor.from_pretrained('nlpconnect/vit-gpt2-image-captioning', cache_dir='/app/hf_cache'); \
    AutoTokenizer.from_pretrained('nlpconnect/vit-gpt2-image-captioning', cache_dir='/app/hf_cache')"

# Copy app code
COPY . .

# Expose port
EXPOSE 8080

# Run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "300", "--workers", "1", "--threads", "4", "app:app"]
