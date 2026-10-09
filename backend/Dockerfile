FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl libglib2.0-0 libxcb1 libgl1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-optional.txt ./
RUN pip install -r requirements.txt
# Optional heavy AI components (sentence-transformers + faster-whisper pull in PyTorch/CTranslate2, ~2 GB).
ARG INSTALL_OPTIONAL=false
RUN if [ "$INSTALL_OPTIONAL" = "true" ]; then pip install -r requirements-optional.txt; fi

COPY . .
# MediaPipe FaceLandmarker model (small). If the download fails the app falls back to OpenCV Haar cascades.
ARG FACE_MODEL_URL=https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
RUN mkdir -p data && (curl -fsSL "$FACE_MODEL_URL" -o data/face_landmarker.task || echo "face model download skipped")

RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 5000
# One worker + threads: per-session state (behaviour tracker) lives in process memory.
CMD ["gunicorn", "-w", "1", "--threads", "8", "-t", "180", "-b", "0.0.0.0:5000", "app:create_app()"]
