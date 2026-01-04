from flask import Flask, render_template, request, send_file, Response
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
from PIL import Image
import torch
import gtts
import os
import uuid
import logging
from queue import Queue, Empty
import threading

app = Flask(__name__)

# -----------------------
# Logging
# -----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("picsonify")

log_queue = Queue()

def log(msg):
    logger.info(msg)
    log_queue.put(msg)

# -----------------------
# Directories (Cloud Run safe)
# -----------------------
UPLOAD_DIR = "/tmp/images"
AUDIO_DIR = "/tmp/audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# -----------------------
# Device
# -----------------------
device = torch.device("cpu")

# -----------------------
# Model (GLOBAL + LAZY)
# -----------------------
model = None
feature_extractor = None
tokenizer = None
model_lock = threading.Lock()

def load_model():
    global model, feature_extractor, tokenizer
    if model is None:
        with model_lock:
            if model is None:  # double check
                log("🔄 Loading model (one-time)")
                model = VisionEncoderDecoderModel.from_pretrained(
                    "nlpconnect/vit-gpt2-image-captioning"
                ).to(device)

                feature_extractor = ViTImageProcessor.from_pretrained(
                    "nlpconnect/vit-gpt2-image-captioning"
                )
                tokenizer = AutoTokenizer.from_pretrained(
                    "nlpconnect/vit-gpt2-image-captioning"
                )
                log("✅ Model ready")

# -----------------------
# Prediction
# -----------------------
def process_image_task(image_path):
    load_model()

    log("📥 Image received")
    image = Image.open(image_path).convert("RGB")

    log("🖼️ Preprocessing")
    pixel_values = feature_extractor(
        images=[image], return_tensors="pt"
    ).pixel_values.to(device)

    log("🤖 Generating caption")
    output_ids = model.generate(
        pixel_values,
        max_length=16,
        num_beams=4
    )

    caption = tokenizer.decode(
        output_ids[0], skip_special_tokens=True
    )

    if not caption.strip():
        caption = "No caption generated"

    log(f"📝 Caption: {caption}")

    log("🔊 Generating audio")
    audio_name = f"{uuid.uuid4().hex}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_name)
    gtts.gTTS(text=caption, lang="en").save(audio_path)

    log("✅ Audio ready")
    return caption, audio_name

# -----------------------
# Routes
# -----------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("imagefile")
        if not file:
            return "No image uploaded", 400

        image_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.jpg")
        file.save(image_path)

        caption, audio_file = process_image_task(image_path)

        return render_template(
            "index.html",
            prediction=caption,
            audio_filename=audio_file
        )

    return render_template("index.html")

@app.route("/get_audio/<filename>")
def get_audio(filename):
    return send_file(
        os.path.join(AUDIO_DIR, filename),
        mimetype="audio/mpeg"
    )

# -----------------------
# SSE Logs (NON-BLOCKING)
# -----------------------
@app.route("/logs")
def logs():
    def stream():
        while True:
            try:
                msg = log_queue.get(timeout=0.5)
                yield f"data: {msg}\n\n"
            except Empty:
                yield ":\n\n"  # keep-alive
    return Response(stream(), mimetype="text/event-stream")

# -----------------------
# Entry
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)
