# SafeZone AI — Local Inference Setup

Real-time CCTV anomaly detection.
SlowFast (video) + PANNs (audio) → SAFE / WARNING / DANGER + SMS.

---

## 1. Folder Structure

```
safezone_ai/
├── backend/
│   ├── main.py          ← FastAPI server (entry point)
│   └── schemas.py
├── models/
│   ├── slowfast_model.py
│   ├── panns_model.py   ← pretrained AudioSet weights, no retraining
│   └── fusion.py
├── data/
│   ├── video_preprocessor.py
│   └── audio_preprocessor.py
├── services/
│   └── temporal_engine.py
├── utils/
│   ├── alerts.py
│   └── logger.py
├── weights/             ← PUT YOUR .pth FILES HERE
│   ├── slowfast_ucfcrime.pth
│   └── Cnn14_mAP=0.431.pth
├── config.py
├── .env                 ← copy from .env.example, add Twilio keys
└── requirements.txt
```

---

## 2. Install

```bash
pip install -r requirements.txt
```

**ffmpeg** must also be installed for audio extraction:
```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org and add to PATH
```

---

## 3. Download PANNs Pretrained Weights

```bash
# Download Cnn14_mAP=0.431.pth from Zenodo
wget https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth \
     -O weights/Cnn14_mAP=0.431.pth
```

---

## 4. Configure Twilio (Optional — for SMS alerts)

```bash
cp .env.example .env
# Edit .env and fill in TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, ALERT_TO
```

If Twilio is not configured, alerts are logged locally but no SMS is sent.

---

## 5. Run the Server

```bash
# From the safezone_ai/ directory
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Development (auto-reload on code changes)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: **http://localhost:8000/docs**

---

## 6. Usage

### Upload a video file

```bash
curl -X POST http://localhost:8000/analyze \
     -F "file=@/path/to/video.mp4"
```

Response:
```json
{
  "filename": "video.mp4",
  "frames_sampled": 32,
  "audio_available": true,
  "fusion": {
    "risk_level": "DANGER",
    "risk_score": 0.812,
    "top_video": "fighting",
    "video_conf": 0.73,
    "top_audio": "scream",
    "audio_conf": 0.68,
    ...
  },
  "alert_sent": true,
  "processing_ms": 340.5
}
```

### Connect a live CCTV camera

```bash
# Start RTSP stream
curl -X POST http://localhost:8000/stream/start \
     -H "Content-Type: application/json" \
     -d '{"rtsp_url": "rtsp://192.168.1.100:554/stream", "camera_id": "cam1"}'

# Poll for results
curl http://localhost:8000/stream/status

# Stop
curl -X POST http://localhost:8000/stream/stop
```

### Use webcam (index 0)

```bash
curl -X POST http://localhost:8000/stream/start \
     -H "Content-Type: application/json" \
     -d '{"rtsp_url": "0", "camera_id": "webcam"}'
```

---

## 7. Key Design Decisions

| Decision | Reason |
|---|---|
| PANNs pretrained (527→5 mapping) | No audio dataset needed — AudioSet classes are specific enough |
| Temporal engine instead of MIL | Model trained clip-level, not with MIL ranking loss |
| Background thread for CCTV | Keeps FastAPI async loop free for other requests |
| Slow/Fast dual pathway | Must match exactly how training built slow/fast tensors |
| Fusion kept from original | Well-designed rule-based scoring, no changes needed |
