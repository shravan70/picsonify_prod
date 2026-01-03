from flask import Flask, render_template, request, send_file, Response
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
from PIL import Image
import torch
import gtts
import os
import uuid
import logging
from queue import Queue, Empty

app = Flask(__name__)

# -----------------------
# Logging setup
# -----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log_queue = Queue()

def log(message):
    logger.info(message)          # Terminal / Cloud logs
    log_queue.put(message)        # UI logs

# -----------------------
# Configuration
# -----------------------
UPLOAD_DIR = os.path.join(os.getcwd(), "images")    # Folder to save uploaded images
AUDIO_DIR = os.path.join(os.getcwd(), "Sound")     # Folder to save generated audio
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

device = torch.device("cpu")  # CPU for portability

# -----------------------
# Load Model once
# -----------------------
log("🔄 Loading image captioning model...")
model = VisionEncoderDecoderModel.from_pretrained(
    "nlpconnect/vit-gpt2-image-captioning"
).to(device)
feature_extractor = ViTImageProcessor.from_pretrained(
    "nlpconnect/vit-gpt2-image-captioning"
)
tokenizer = AutoTokenizer.from_pretrained(
    "nlpconnect/vit-gpt2-image-captioning"
)
log("✅ Model loaded successfully")

# -----------------------
# Prediction + Audio Generation
# -----------------------
def predict_and_generate_audio(image_path):
    try:
        log("📥 Image received")

        log("🖼️ Preprocessing image")
        image = Image.open(image_path).convert("RGB")
        pixel_values = feature_extractor(
            images=[image], return_tensors="pt"
        ).pixel_values.to(device)

        log("🤖 Generating caption")
        output_ids = model.generate(
            pixel_values,
            max_length=16,
            num_beams=4
        )
        prediction = tokenizer.decode(output_ids[0], skip_special_tokens=True)

        if not prediction.strip():
            prediction = "No caption generated"

        log(f"📝 Caption generated: {prediction}")

        log("🔊 Generating audio")
        audio_filename = f"{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)
        gtts.gTTS(text=prediction, lang="en").save(audio_path)
        log("✅ Audio generated successfully")

        return prediction, audio_filename
    except Exception as e:
        log(f"❌ Error in prediction: {e}")
        raise

# -----------------------
# Routes
# -----------------------
@app.route("/", methods=["GET", "POST"])
def process_image():
    if request.method == "POST":
        imagefile = request.files.get("imagefile")
        if not imagefile or imagefile.filename == "":
            return "No image uploaded", 400

        image_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.jpg")
        imagefile.save(image_path)

        try:
            prediction, audio_filename = predict_and_generate_audio(image_path)
        except Exception as e:
            return f"Internal Server Error: {e}", 500

        # Render template directly to avoid audio replay on redirect
        return render_template("index.html", prediction=prediction, audio_filename=audio_filename)

    return render_template("index.html")

@app.route("/get_audio/<filename>")
def get_audio(filename):
    audio_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(audio_path):
        return "Audio file not found", 404
    return send_file(audio_path, mimetype="audio/mpeg")

# -----------------------
# SSE Log Streaming
# -----------------------
@app.route("/logs")
def stream_logs():
    def event_stream():
        while True:
            try:
                message = log_queue.get(timeout=1)
                yield f"data: {message}\n\n"
            except Empty:
                continue
    return Response(event_stream(), mimetype="text/event-stream")

# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
