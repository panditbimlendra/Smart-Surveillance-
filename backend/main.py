"""
SafeZone AI — Production FastAPI Inference Server
==================================================
Supports two operational modes:

  MODE A — File Upload  (POST /analyze)
    Upload any video file (.mp4 / .avi / etc.)
    → extract frames + audio
    → SlowFast video inference (14 UCF-Crime classes)
    → PANNs audio inference (mapped to 5 classes)
    → FusionEngine → SAFE / WARNING / DANGER
    → AlertSystem (Twilio SMS if DANGER)
    → Return full JSON result

  MODE B — Live CCTV Stream  (POST /stream/start)
    Provide an RTSP URL (or 0 for webcam)
    → Background thread reads frames continuously
    → Every 8 frames: run SlowFast inference
    → Temporal decision engine (no single-spike false alarms)
    → AlertSystem fires SMS when DANGER persists
    → Poll GET /stream/status for latest result
    → Stop with POST /stream/stop

  BONUS MODE — WebSocket  (WS /ws/stream)
    Send base64-encoded JPEG frames from any client
    → per-frame inference + full result pushed back
    → Useful for browser-based or mobile frontends

Run:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

Swagger UI:  http://localhost:8000/docs
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from typing import Optional

import cv2
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, File, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ── SafeZone imports ──────────────────────────────────────────────
from config import VCFG, ACFG, FCFG, ALCFG, SCFG, PATHS, DEVICE
from models.slowfast_model import SlowFastLitModel
from models.panns_model import PANNsInference
from models.fusion import FusionEngine
from data.video_preprocessor import (
    frames_to_slowfast,
    load_frames_from_file,
    FrameBuffer,
)
from data.audio_preprocessor import (
    LogMelConverter,
    load_audio_from_video,
    waveform_to_tensor,
    silence_tensor,
)
from services.temporal_engine import TemporalEngine
from utils.alerts import AlertSystem
from utils.logger import get_logger
from backend.schemas import (
    AlertListItem,
    AnalyzeResponse,
    FusionResult,
    HealthResponse,
    LogListItem,
    PredictRequest,
    PredictResponse,
    StreamStartRequest,
    StreamStartResponse,
    StreamStatusResponse,
    StreamStopResponse,
    WsResultMessage,
)

# Create log/temp directories
os.makedirs(PATHS.log_dir, exist_ok=True)
os.makedirs(PATHS.temp_dir, exist_ok=True)

logger = get_logger("safezone.server", PATHS.app_log)

_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}


def _neutral_video_preds() -> dict[str, float]:
    """Return a video distribution for audio-only uploads."""
    preds = {cls: 0.0 for cls in VCFG.classes}
    preds["normal"] = 1.0
    return preds


# ══════════════════════════════════════════════════════════════════
#  MODEL WRAPPERS
# ══════════════════════════════════════════════════════════════════

class VideoInference:
    """
    Wraps SlowFastLitModel for per-clip inference.

    Key correctness fix vs original main.py:
      SlowFastLitModel.forward(slow, fast) takes TWO separate tensors.
      The original code incorrectly passed a single tensor. Fixed here.
    """

    def __init__(self, weights_path: str, device: torch.device = DEVICE):
        self._device = device
        self._model  = SlowFastLitModel(cfg=VCFG)
        self._load(weights_path)
        self._model.to(device).eval()

    def _load(self, path: str) -> None:
        if not os.path.exists(path):
            logger.warning(
                "Video weights not found at '%s'. "
                "Running with random weights — predictions will be meaningless.",
                path,
            )
            return
        state = torch.load(path, map_location="cpu")
        # Handle both raw state_dict and Lightning checkpoint format
        if "state_dict" in state:
            state = state["state_dict"]
        missing, unexpected = self._model.load_state_dict(state, strict=False)
        if missing:
            logger.warning("Video model — missing keys: %d  (first 5: %s)", len(missing), missing[:5])
        if unexpected:
            logger.warning("Video model — unexpected keys: %d", len(unexpected))
        logger.info("Video weights loaded from '%s'", path)

    @torch.no_grad()
    def predict(self, frames_np: np.ndarray) -> dict:
        """
        Args:
            frames_np : (T, H, W, 3) float32, normalised, from video_preprocessor

        Returns:
            {class_name: probability}  — 14 UCF-Crime classes
        """
        slow, fast = frames_to_slowfast(frames_np, VCFG)
        slow = slow.to(self._device)
        fast = fast.to(self._device)

        logits = self._model(slow, fast)                         # (1, 14)
        probs  = torch.softmax(logits, dim=1)[0].cpu().numpy()  # (14,)

        return {cls: float(p) for cls, p in zip(VCFG.classes, probs)}


# ══════════════════════════════════════════════════════════════════
#  CCTV BACKGROUND STREAMER
# ══════════════════════════════════════════════════════════════════

class CCTVStreamer:
    """
    Background thread that reads from an RTSP camera (or webcam),
    runs inference, and fires alerts.

    Audio note:
      OpenCV does not decode audio from RTSP streams. Therefore
      CCTV mode uses video-only inference and returns neutral
      audio predictions (all "normal").  The fusion still works
      correctly — the video model carries the full detection load.
      To add audio, you would need a separate ffmpeg process.

    Thread safety:
      _last_result and counters are updated atomically (Python GIL
      protects simple attribute assignments on CPython). For multi-
      process deployments use a proper message queue instead.
    """

    def __init__(
        self,
        rtsp_url      : str,
        camera_id     : str,
        video_inf     : VideoInference,
        audio_inf     : PANNsInference,
        fusion        : FusionEngine,
        alerts        : AlertSystem,
    ):
        self._url           = rtsp_url
        self._camera_id     = camera_id
        self._video_inf     = video_inf
        self._audio_inf     = audio_inf
        self._fusion        = fusion
        self._alerts        = alerts

        self._stop_event    = threading.Event()
        self._thread        : Optional[threading.Thread] = None
        self._lock          = threading.Lock()

        # Status (read from status endpoint)
        self._frames_processed = 0
        self._clips_processed  = 0
        self._last_result      : Optional[dict] = None
        self._last_alert_ts    : Optional[float] = None
        self._last_error       : Optional[str] = None
        self._last_frame_jpeg  : Optional[bytes] = None
        self._temporal         = TemporalEngine()
        self._started_event    = threading.Event()

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Stream already running. Stop it first.")
        self._stop_event.clear()
        self._started_event.clear()
        self._temporal.reset()
        self._frames_processed = 0
        self._clips_processed  = 0
        self._last_result      = None
        self._last_alert_ts    = None
        self._last_error       = None
        self._last_frame_jpeg  = None
        self._thread = threading.Thread(
            target  = self._run,
            name    = f"cctv-{self._camera_id}",
            daemon  = True,    # dies if main process exits
        )
        self._thread.start()
        self._started_event.wait(timeout=3.0)
        if self._last_error:
            raise RuntimeError(self._last_error)
        if not self.is_running:
            raise RuntimeError("Camera did not stay running. Check whether the source is valid and available.")
        logger.info("CCTVStreamer started — url=%s  camera=%s", self._url, self._camera_id)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("CCTVStreamer stopped — camera=%s", self._camera_id)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Status ────────────────────────────────────────────────

    def get_status(self) -> dict:
        with self._lock:
            last = self._last_result.copy() if self._last_result else None
        return {
            "streaming"        : self.is_running,
            "rtsp_url"         : self._url,
            "camera_id"        : self._camera_id,
            "frames_processed" : self._frames_processed,
            "clips_processed"  : self._clips_processed,
            "temporal_summary" : self._temporal.summary(),
            "last_result"      : last,
            "last_alert_ts"    : self._last_alert_ts,
            "error_message"    : self._last_error,
        }

    def get_latest_frame(self) -> Optional[bytes]:
        with self._lock:
            return bytes(self._last_frame_jpeg) if self._last_frame_jpeg else None

    # ── Main loop (runs in background thread) ─────────────────

    def _run(self) -> None:
        # Accept both RTSP URLs and integer indices (webcam)
        src = int(self._url) if self._url.isdigit() else self._url
        cap = cv2.VideoCapture(src)

        if not cap.isOpened():
            self._last_error = f"Could not open camera source '{self._url}'. Close other apps using the camera, then try again."
            self._started_event.set()
            logger.error("CCTVStreamer: cannot open source '%s'", self._url)
            return

        self._last_error = None
        self._started_event.set()

        frame_buf = FrameBuffer(
            clip_length = VCFG.frames,   # 32
            stride      = VCFG.frames // 4,  # 8 — run inference every 8 new frames
            frame_size  = VCFG.frame_size,   # 224
        )

        logger.info("CCTVStreamer: capture opened — %s", self._url)

        while not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                self._last_error = "Camera stream opened but frames could not be read. Check camera permissions or RTSP availability."
                logger.warning("CCTVStreamer: frame read failed — retrying in 1s")
                time.sleep(1.0)
                continue

            self._last_error = None
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok:
                with self._lock:
                    self._last_frame_jpeg = encoded.tobytes()
            frame_buf.add(frame)
            self._frames_processed += 1

            if frame_buf.is_ready():
                self._process_clip(frame_buf.get_clip())

        cap.release()
        logger.info("CCTVStreamer: capture released — %s", self._url)

    def _process_clip(self, frames_np: np.ndarray) -> None:
        """Run the full inference pipeline on one clip."""
        try:
            # Video inference
            video_preds = self._video_inf.predict(frames_np)

            # Audio: CCTV mode is video-only — return neutral audio
            audio_preds = self._audio_inf.predict_silence()

            # Fuse video + audio
            fusion_result = self._fusion.fuse(video_preds, audio_preds)

            # Temporal decision engine (prevents single-spike false alerts)
            self._temporal.update(fusion_result["risk_score"])
            is_anomaly, confidence = self._temporal.decision()

            # Override fusion's should_alert with the temporal decision
            if is_anomaly:
                fusion_result["should_alert"] = True
                if fusion_result["risk_level"] == "SAFE":
                    fusion_result["risk_level"] = "WARNING"

            # Fire alert if needed (AlertSystem handles cooldown internally)
            alert_sent = self._alerts.maybe_alert(fusion_result)
            if alert_sent:
                self._last_alert_ts = time.time()

            # Store for status endpoint
            with self._lock:
                self._last_result = fusion_result.copy()

            self._clips_processed += 1

            logger.debug(
                "Clip %d  risk=%s (%.3f)  top=%s  alert=%s",
                self._clips_processed,
                fusion_result["risk_level"],
                fusion_result["risk_score"],
                fusion_result["top_video"],
                alert_sent,
            )

        except Exception as e:
            self._last_error = str(e)
            logger.error("CCTVStreamer._process_clip error: %s", e, exc_info=True)


# ══════════════════════════════════════════════════════════════════
#  APP STATE  (holds models + stream — lives for the app lifetime)
# ══════════════════════════════════════════════════════════════════

class AppState:
    """Singleton holding all loaded models and the CCTV streamer."""
    video_inf  : VideoInference
    audio_inf  : PANNsInference
    fusion     : FusionEngine
    alerts     : AlertSystem
    streamer   : Optional[CCTVStreamer] = None


# ══════════════════════════════════════════════════════════════════
#  LIFESPAN — load models once at startup
# ══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SafeZone AI — startup  (device=%s)", DEVICE)

    state = AppState()
    state.video_inf = VideoInference(PATHS.video_weights, DEVICE)
    state.audio_inf = PANNsInference(PATHS.audio_weights, DEVICE)
    state.fusion    = FusionEngine(FCFG, weights_path=PATHS.fusion_weights or None)
    state.alerts    = AlertSystem(ALCFG, camera_id=ALCFG.camera_label)

    app.state.ctx = state
    logger.info("All models loaded. API ready.")

    yield   # ← server runs here

    # Cleanup on shutdown
    logger.info("SafeZone AI — shutdown")
    if state.streamer and state.streamer.is_running:
        state.streamer.stop()


# ══════════════════════════════════════════════════════════════════
#  FASTAPI APP
# ══════════════════════════════════════════════════════════════════

app = FastAPI(
    title       = "SafeZone AI",
    description = (
        "Real-time CCTV anomaly detection.\n"
        "14-class video (SlowFast) + 5-class audio (PANNs) → "
        "SAFE / WARNING / DANGER + Twilio SMS."
    ),
    version     = "2.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # tighten in production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ══════════════════════════════════════════════════════════════════
#  HELPER: get typed AppState from request
# ══════════════════════════════════════════════════════════════════

def _state(app_) -> AppState:
    return app_.state.ctx


def _read_audit_entries(limit: int = 100) -> list[dict]:
    """Read the most recent audit entries from the JSONL file."""
    if not os.path.exists(PATHS.audit_log):
        return []

    entries: list[dict] = []
    with open(PATHS.audit_log, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping invalid audit log line.")

    return list(reversed(entries[-limit:]))


def _severity_from_risk(risk_level: str) -> str:
    mapping = {"DANGER": "high", "WARNING": "medium", "SAFE": "low"}
    return mapping.get((risk_level or "").upper(), "low")


def _status_from_risk(risk_level: str) -> str:
    mapping = {"DANGER": "ACTIVE", "WARNING": "REVIEW", "SAFE": "LOGGED"}
    return mapping.get((risk_level or "").upper(), "LOGGED")


def _log_type_from_entry(entry: dict) -> str:
    top_audio = (entry.get("top_audio") or "").lower()
    if top_audio and top_audio != "normal":
        return "AUDIO"

    top_video = (entry.get("top_video") or "").lower()
    if top_video in {"stealing", "shoplifting", "robbery", "burglary"}:
        return "ACCESS"
    if top_video in {"abuse", "assault", "fighting", "shooting", "arson", "explosion"}:
        return "THREAT"
    return "SYSTEM" if top_video == "normal" else "BEHAVIOR"


def _alert_item_from_entry(entry: dict, idx: int) -> AlertListItem:
    risk_level = (entry.get("risk_level") or "SAFE").upper()
    risk_score = float(entry.get("risk_score", 0.0))
    top_video = entry.get("top_video", "normal")
    top_audio = entry.get("top_audio", "normal")
    camera = entry.get("camera", "SafeZone Camera 1")
    iso_time = entry.get("iso", "")
    time_str = iso_time.split("T")[-1] if "T" in iso_time else iso_time

    return AlertListItem(
        id=str(entry.get("ts", idx)),
        type=f"{risk_level.title()} Risk",
        message=f"Video: {top_video} | Audio: {top_audio} | Risk: {risk_score:.0%}",
        location=camera,
        camera=camera,
        time=time_str,
        severity=_severity_from_risk(risk_level),
    )


def _log_item_from_entry(entry: dict, idx: int) -> LogListItem:
    risk_level = (entry.get("risk_level") or "SAFE").upper()
    risk_score = float(entry.get("risk_score", 0.0))
    top_video = entry.get("top_video", "normal")
    camera = entry.get("camera", "SafeZone Camera 1")
    iso_time = entry.get("iso", "")
    time_str = iso_time.split("T")[-1] if "T" in iso_time else iso_time

    return LogListItem(
        id=str(entry.get("ts", idx)),
        time=time_str,
        event=f"{risk_level.title()} event ({risk_score:.0%})",
        zone=camera,
        camera=camera,
        type=_log_type_from_entry(entry),
        status=_status_from_risk(risk_level),
    )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT: GET /health
# ══════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse, tags=["Status"])
async def health():
    """Quick liveness check. Confirms all models are loaded."""
    return HealthResponse(
        status        = "ok",
        models_loaded = True,
        device        = str(DEVICE),
        video_weights = PATHS.video_weights,
        audio_weights = PATHS.audio_weights,
        timestamp     = time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


@app.get("/alerts/recent", response_model=list[AlertListItem], tags=["Status"])
async def recent_alerts(limit: int = 20):
    """Return recent alerts derived from the audit log."""
    entries = _read_audit_entries(limit=max(1, min(limit, 200)))
    return [_alert_item_from_entry(entry, idx) for idx, entry in enumerate(entries)]


@app.get("/logs/recent", response_model=list[LogListItem], tags=["Status"])
async def recent_logs(limit: int = 50):
    """Return recent event log rows derived from the audit log."""
    entries = _read_audit_entries(limit=max(1, min(limit, 500)))
    return [_log_item_from_entry(entry, idx) for idx, entry in enumerate(entries)]


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT: POST /analyze  — video file upload
# ══════════════════════════════════════════════════════════════════

@app.post("/analyze", response_model=AnalyzeResponse, tags=["File Upload"])
async def analyze(file: UploadFile = File(...)):
    """
    Upload a video file and receive a full risk analysis.

    Accepts: .mp4, .avi, .mkv, or any OpenCV-readable format.
    Returns: SAFE / WARNING / DANGER with per-class probabilities
             and an alert flag (Twilio SMS fired if DANGER).
    """
    state = _state(app)
    t0    = time.time()

    # Save upload to temp file
    suffix   = os.path.splitext(file.filename)[1] or ".mp4"
    tmp_path = os.path.join(PATHS.temp_dir, f"upload_{int(t0*1000)}{suffix}")

    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_ext = os.path.splitext(file.filename or "")[1].lower()
        is_audio_upload = (
            file_ext in _AUDIO_EXTENSIONS
            or (file.content_type or "").startswith("audio/")
        )

        # ── VIDEO: load frames ─────────────────────────────────
        frames_np = await asyncio.get_event_loop().run_in_executor(
            None,
            load_frames_from_file,
            tmp_path,
            VCFG.frames,
            VCFG.frame_size,
        )

        if frames_np is None and not is_audio_upload:
            raise HTTPException(
                status_code=422,
                detail=f"Could not read frames from '{file.filename}'. "
                       "Upload a valid video, or use a supported audio format such as .mp3 or .wav.",
            )

        # ── VIDEO: inference ───────────────────────────────────
        if frames_np is not None:
            video_preds = await asyncio.get_event_loop().run_in_executor(
                None, state.video_inf.predict, frames_np
            )
            frames_sampled = VCFG.frames
        else:
            video_preds = _neutral_video_preds()
            frames_sampled = 0

        # ── AUDIO: extract + inference ─────────────────────────
        waveform = await asyncio.get_event_loop().run_in_executor(
            None,
            load_audio_from_video,
            tmp_path,
            ACFG.sample_rate,
            None,
        )

        audio_available = waveform is not None

        if audio_available:
            try:
                audio_preds = await asyncio.get_event_loop().run_in_executor(
                    None, state.audio_inf.predict, waveform
                )
            except Exception as e:
                logger.warning(
                    "Audio inference failed for '%s': %s. Falling back to silence.",
                    file.filename,
                    e,
                )
                audio_available = False
                audio_preds = state.audio_inf.predict_silence()
        else:
            audio_preds = state.audio_inf.predict_silence()

        # ── FUSION ────────────────────────────────────────────
        fusion_result = state.fusion.fuse(video_preds, audio_preds)

        # ── ALERT ─────────────────────────────────────────────
        alert_sent = state.alerts.maybe_alert(fusion_result)

        processing_ms = (time.time() - t0) * 1000
        logger.info(
            "ANALYZE '%s'  →  %s (%.3f)  audio=%s  alert=%s  %.0fms",
            file.filename,
            fusion_result["risk_level"],
            fusion_result["risk_score"],
            "yes" if audio_available else "no",
            alert_sent,
            processing_ms,
        )

        return AnalyzeResponse(
            filename        = file.filename,
            frames_sampled  = frames_sampled,
            audio_available = audio_available,
            fusion          = FusionResult(**fusion_result),
            alert_sent      = alert_sent,
            processing_ms   = round(processing_ms, 1),
        )

    finally:
        # Always remove temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT: POST /predict  — raw dict fusion test
# ══════════════════════════════════════════════════════════════════

@app.post("/predict", response_model=PredictResponse, tags=["Debug"])
async def predict(request: PredictRequest):
    """
    Test the FusionEngine directly by supplying pre-computed predictions.
    Useful for debugging thresholds without running full inference.
    """
    state  = _state(app)
    result = state.fusion.fuse(request.video_preds, request.audio_preds)
    return PredictResponse(**result)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT: POST /stream/start  — start CCTV background stream
# ══════════════════════════════════════════════════════════════════

@app.post("/stream/start", response_model=StreamStartResponse, tags=["CCTV Stream"])
async def stream_start(request: StreamStartRequest):
    """
    Connect to a live RTSP camera (or webcam) and start continuous detection.

    - rtsp_url  : RTSP URL  e.g. "rtsp://192.168.1.100:554/stream"
                  OR integer string "0" / "1" for webcam index.
    - camera_id : label used in alerts and audit log (default "cam1")

    Uses a background thread — this endpoint returns immediately.
    Poll GET /stream/status for results.
    """
    state = _state(app)

    if state.streamer and state.streamer.is_running:
        raise HTTPException(
            status_code=409,
            detail="A stream is already running. Stop it first with POST /stream/stop.",
        )

    state.streamer = CCTVStreamer(
        rtsp_url  = request.rtsp_url,
        camera_id = request.camera_id,
        video_inf = state.video_inf,
        audio_inf = state.audio_inf,
        fusion    = state.fusion,
        alerts    = state.alerts,
    )

    try:
        state.streamer.start()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start stream: {e}")

    return StreamStartResponse(
        status    = "started",
        rtsp_url  = request.rtsp_url,
        camera_id = request.camera_id,
        message   = "Stream running in background. Poll GET /stream/status for results.",
    )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT: POST /stream/stop
# ══════════════════════════════════════════════════════════════════

@app.post("/stream/stop", response_model=StreamStopResponse, tags=["CCTV Stream"])
async def stream_stop():
    """Stop the running CCTV background stream."""
    state = _state(app)

    if not state.streamer or not state.streamer.is_running:
        return StreamStopResponse(
            status  = "not_running",
            message = "No stream was running.",
        )

    await asyncio.get_event_loop().run_in_executor(None, state.streamer.stop)
    state.streamer = None

    return StreamStopResponse(
        status  = "stopped",
        message = "Stream stopped successfully.",
    )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINT: GET /stream/status
# ══════════════════════════════════════════════════════════════════

@app.get("/stream/status", response_model=StreamStatusResponse, tags=["CCTV Stream"])
async def stream_status():
    """
    Poll this endpoint to get the current stream status and
    the most recent detection result.
    """
    state = _state(app)

    if not state.streamer:
        return StreamStatusResponse(
            streaming        = False,
            frames_processed = 0,
            clips_processed  = 0,
            temporal_summary = {},
        )

    s = state.streamer.get_status()

    last_fusion = None
    if s["last_result"]:
        last_fusion = FusionResult(**s["last_result"])

    return StreamStatusResponse(
        streaming        = s["streaming"],
        rtsp_url         = s["rtsp_url"],
        camera_id        = s["camera_id"],
        frames_processed = s["frames_processed"],
        clips_processed  = s["clips_processed"],
        temporal_summary = s["temporal_summary"],
        last_result      = last_fusion,
        last_alert_ts    = s["last_alert_ts"],
        error_message    = s["error_message"],
    )


@app.get("/stream/frame", tags=["CCTV Stream"])
async def stream_frame():
    """
    Return the most recent camera frame as a JPEG image for dashboard preview.
    """
    state = _state(app)

    if not state.streamer or not state.streamer.is_running:
        raise HTTPException(status_code=404, detail="No active stream is running.")

    frame_jpeg = state.streamer.get_latest_frame()
    if not frame_jpeg:
        raise HTTPException(status_code=404, detail="Waiting for the first camera frame.")

    return Response(content=frame_jpeg, media_type="image/jpeg")


# ══════════════════════════════════════════════════════════════════
#  WEBSOCKET: WS /ws/stream  — for browser/mobile frontends
# ══════════════════════════════════════════════════════════════════

@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time inference from a browser or mobile app.

    Client sends JSON:
        { "frame": "<base64 JPEG>",  "audio": [f32, f32, ...] }

    Server responds with JSON (WsResultMessage) after each inference.

    Audio is optional — if absent, neutral audio is assumed.
    Inference runs every `stride` frames to avoid GPU thrashing.
    """
    await websocket.accept()
    state  = _state(app)
    client = websocket.client
    logger.info("WebSocket connected: %s", client)

    # Per-connection state
    frame_buf    = FrameBuffer(
        clip_length = VCFG.frames,
        stride      = VCFG.frames // 4,
        frame_size  = VCFG.frame_size,
    )
    temporal     = TemporalEngine()
    loop         = asyncio.get_event_loop()
    converter    = LogMelConverter(ACFG)

    try:
        while True:
            raw  = await websocket.receive_text()
            data = json.loads(raw)
            resp : dict = {"ts": time.time(), "alert_sent": False, "cooldown_remaining": 0.0}

            # ── Video frame ──────────────────────────────────────
            if "frame" in data:
                frame_bgr = _b64_to_frame(data["frame"])
                if frame_bgr is not None:
                    frame_buf.add(frame_bgr)

                    if frame_buf.is_ready():
                        frames_np   = frame_buf.get_clip()
                        video_preds = await loop.run_in_executor(
                            None, state.video_inf.predict, frames_np
                        )
                        resp["video"] = video_preds

                        # Audio
                        if "audio" in data and data["audio"]:
                            waveform    = np.array(data["audio"], dtype=np.float32)
                            audio_preds = await loop.run_in_executor(
                                None, state.audio_inf.predict, waveform
                            )
                        else:
                            audio_preds = state.audio_inf.predict_silence()

                        resp["audio"] = audio_preds

                        # Fuse
                        fusion_result = state.fusion.fuse(video_preds, audio_preds)

                        # Temporal decision
                        temporal.update(fusion_result["risk_score"])
                        is_anomaly, confidence = temporal.decision()
                        if is_anomaly:
                            fusion_result["should_alert"] = True

                        alert_sent = state.alerts.maybe_alert(fusion_result)

                        resp["fusion"]             = fusion_result
                        resp["alert_sent"]         = alert_sent
                        resp["cooldown_remaining"] = round(state.alerts.cooldown_remaining(), 1)
                        resp["temporal_summary"]   = temporal.summary()

            await websocket.send_text(json.dumps(resp, default=str))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", client)
    except Exception as e:
        logger.error("WebSocket error (%s): %s", client, e, exc_info=True)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _b64_to_frame(b64_str: str) -> Optional[np.ndarray]:
    """Decode a base64-encoded JPEG string to a BGR numpy array."""
    try:
        buf = np.frombuffer(base64.b64decode(b64_str), np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception as e:
        logger.warning("Frame decode error: %s", e)
        return None


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host      = SCFG.host,
        port      = SCFG.port,
        log_level = "info",
        reload    = False,   # set True during development
    )
