"""SafeZone AI — API Request / Response Schemas"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────

class FusionResult(BaseModel):
    """Full result from FusionEngine.fuse()"""
    risk_score   : float
    risk_level   : str                         # SAFE / WARNING / DANGER
    top_video    : str
    video_conf   : float
    top_audio    : str
    audio_conf   : float
    rule_score   : float
    mlp_score    : Optional[float] = None
    should_alert : bool
    video_preds  : Optional[Dict[str, float]] = None
    audio_preds  : Optional[Dict[str, float]] = None


class AudioDetectionItem(BaseModel):
    label_key  : str
    label      : str
    confidence : float
    severity   : str
    action     : str
    start_time : float
    end_time   : float


# ── File Upload Endpoint  POST /analyze ──────────────────────────

class AnalyzeResponse(BaseModel):
    """Response from POST /analyze (video file upload)"""
    filename       : str
    duration_secs  : Optional[float] = None
    frames_sampled : int
    audio_available: bool
    audio_detections: List[AudioDetectionItem] = Field(default_factory=list)
    fusion         : FusionResult
    alert_sent     : bool
    processing_ms  : float   # wall-clock time for the full pipeline


class AlertListItem(BaseModel):
    id       : str
    type     : str
    message  : str
    location : str
    camera   : str
    time     : str
    severity : str


class LogListItem(BaseModel):
    id     : str
    time   : str
    event  : str
    zone   : str
    camera : str
    type   : str
    status : str


# ── CCTV Stream Endpoints ────────────────────────────────────────

class StreamStartRequest(BaseModel):
    rtsp_url   : str  = Field(...,   example="rtsp://192.168.1.100:554/stream")
    camera_id  : str  = Field("cam1", example="cam1")


class WebcamStartRequest(BaseModel):
    """Request to start laptop/local webcam streaming"""
    device_id  : int  = Field(0, example=0)  # 0 = default webcam, 1 = secondary, etc.
    camera_id  : str  = Field("laptop_webcam", example="laptop_webcam")


class StreamStartResponse(BaseModel):
    status    : str
    rtsp_url  : str
    camera_id : str
    message   : str


class StreamStopResponse(BaseModel):
    status  : str
    message : str


class StreamStatusResponse(BaseModel):
    streaming       : bool
    rtsp_url        : Optional[str] = None
    camera_id       : Optional[str] = None
    frames_processed: int
    clips_processed : int
    temporal_summary: Dict[str, Any]
    last_result     : Optional[FusionResult] = None
    last_alert_ts   : Optional[float] = None
    abnormal_frame_ts: Optional[float] = None  # Timestamp when abnormal activity frame was captured
    abnormal_frame_url: Optional[str] = None   # URL to fetch the abnormal activity frame
    error_message   : Optional[str] = None


# ── WebSocket  WS /ws/stream ─────────────────────────────────────

class WsFrameMessage(BaseModel):
    """Client → Server: a single base64-encoded JPEG frame (optionally with audio)"""
    frame  : str               # base64 JPEG
    audio  : Optional[List[float]] = None   # raw float32 PCM samples if available


class WsResultMessage(BaseModel):
    """Server → Client: per-frame analysis result"""
    ts                : float
    video             : Optional[Dict[str, float]] = None
    audio             : Optional[Dict[str, float]] = None
    fusion            : Optional[FusionResult]     = None
    alert_sent        : bool = False
    cooldown_remaining: float = 0.0
    temporal_summary  : Optional[Dict[str, Any]]  = None


# ── Health Check  GET /health ────────────────────────────────────

class HealthResponse(BaseModel):
    status         : str
    models_loaded  : bool
    device         : str
    video_weights  : str
    audio_weights  : str
    timestamp      : str


# ── Direct fusion test  POST /predict ────────────────────────────

class PredictRequest(BaseModel):
    video_preds : Dict[str, float] = Field(
        ..., example={"fighting": 0.84, "normal": 0.06}
    )
    audio_preds : Dict[str, float] = Field(
        ..., example={"scream": 0.79, "normal": 0.12}
    )

class PredictResponse(BaseModel):
    risk_score   : float
    risk_level   : str
    top_video    : str
    top_audio    : str
    video_conf   : float
    audio_conf   : float
    rule_score   : float
    mlp_score    : Optional[float] = None
    should_alert : bool
    video_preds  : Optional[Dict[str, float]] = None
    audio_preds  : Optional[Dict[str, float]] = None
