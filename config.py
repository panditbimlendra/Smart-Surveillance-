"""
SafeZone AI — Central Configuration
=====================================
All tuneable values live here. Nothing else in the codebase
contains magic numbers. Edit this file only.

For local VS Code inference:
  - Put weights in ./weights/
  - Set Twilio env vars in .env (copy from .env.example)
  - Run: uvicorn backend.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations
import os
import torch
from dataclasses import dataclass, field
from typing import Dict, List

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — set env vars manually

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ─────────────────────────────────────────────────────────────────
#  UCF-Crime class registry
#  Order matters — must match the order used during training
# ─────────────────────────────────────────────────────────────────

UCF_CLASSES: List[str] = [
    "abuse",          # 0  HIGH
    "arrest",         # 1  MEDIUM
    "arson",          # 2  HIGH
    "assault",        # 3  HIGH
    "burglary",       # 4  HIGH
    "explosion",      # 5  HIGH
    "fighting",       # 6  HIGH
    "normal",         # 7  NONE
    "roadaccidents",  # 8  HIGH
    "robbery",        # 9  HIGH
    "shooting",       # 10 HIGH
    "shoplifting",    # 11 MEDIUM
    "stealing",       # 12 MEDIUM
    "vandalism",      # 13 MEDIUM
]

UCF_FOLDER_MAP: Dict[str, str] = {}  # folder name == class name

CLASS_RISK_TIER: Dict[str, str] = {
    "abuse"        : "HIGH",
    "arrest"       : "MEDIUM",
    "arson"        : "HIGH",
    "assault"      : "HIGH",
    "burglary"     : "HIGH",
    "explosion"    : "HIGH",
    "fighting"     : "HIGH",
    "normal"       : "NONE",
    "roadaccidents": "HIGH",
    "robbery"      : "HIGH",
    "shooting"     : "HIGH",
    "shoplifting"  : "MEDIUM",
    "stealing"     : "MEDIUM",
    "vandalism"    : "MEDIUM",
}

TIER_SCORE: Dict[str, float] = {
    "HIGH": 0.90, "MEDIUM": 0.55, "LOW": 0.25, "NONE": 0.00,
}

# 5 audio classes produced by PANNs class mapping
AUDIO_CLASSES: List[str] = [
    "normal", "scream", "explosion", "glass_break", "gunshot",
]

# ─────────────────────────────────────────────────────────────────
#  AudioSet class index mapping → SafeZone 5 classes
#  These map pretrained PANNs 527 AudioSet outputs to our classes.
#  Indices from: https://github.com/qiuqiangkong/audioset_tagging_cnn
# ─────────────────────────────────────────────────────────────────

AUDIOSET_MAP: Dict[str, List[int]] = {
    "gunshot"   : [427, 428],   # Gunshot/gunfire, Machine gun
    "explosion" : [426],        # Explosion
    "scream"    : [80, 81],     # Screaming, Shout
    "glass_break": [461, 462],  # Glass, Chink/clink
    # "normal" is computed as 1 - max(other 4 groups)
}


# ─────────────────────────────────────────────────────────────────
#  Paths — all relative to the project root
# ─────────────────────────────────────────────────────────────────

@dataclass
class Paths:
    # Trained model weights
    video_weights   : str = "weights/slowfast_ucfcrime.pth"
    audio_weights   : str = "weights/Cnn14_mAP=0.431.pth"   # pretrained AudioSet PANNs
    fusion_weights  : str = ""                                # optional MLP fusion; leave blank

    # Logs
    log_dir         : str = "logs"
    audit_log       : str = "logs/audit.jsonl"
    app_log         : str = "logs/safezone.log"

    # Temp upload directory
    temp_dir        : str = "temp"


# ─────────────────────────────────────────────────────────────────
#  Video config — must match training settings exactly
# ─────────────────────────────────────────────────────────────────

@dataclass
class VideoConfig:
    classes             : List[str] = field(default_factory=lambda: UCF_CLASSES)
    frames              : int   = 32       # fast pathway total frames per clip
    frame_size          : int   = 224
    unfreeze_last_n     : int   = 2        # must match what was used in training
    lr                  : float = 3e-4     # not used at inference — kept for model init
    weight_decay        : float = 1e-4
    label_smoothing     : float = 0.1
    epochs              : int   = 20
    grad_clip           : float = 1.0

    @property
    def num_classes(self) -> int:  return len(self.classes)

    @property
    def slow_frames(self) -> int:  return self.frames // 4   # = 8

    @property
    def normal_idx(self) -> int:   return self.classes.index("normal")


# ─────────────────────────────────────────────────────────────────
#  Audio config — used by LogMelConverter only
# ─────────────────────────────────────────────────────────────────

@dataclass
class AudioConfig:
    classes             : List[str] = field(default_factory=lambda: AUDIO_CLASSES)
    sample_rate         : int   = 32000
    chunk_seconds       : float = 2.0
    n_mels              : int   = 64
    n_fft               : int   = 1024
    hop_length          : int   = 320
    fmin                : float = 50.0
    fmax                : float = 14000.0
    # Not used at inference:
    epochs              : int   = 20
    batch_size          : int   = 32
    lr                  : float = 1e-4
    weight_decay        : float = 1e-4
    label_smoothing     : float = 0.1
    mixup_alpha         : float = 0.4
    num_workers         : int   = 4
    early_stop_patience : int   = 7
    unfreeze_last_n     : int   = 2
    val_split           : float = 0.20
    random_seed         : int   = 42

    @property
    def chunk_samples(self) -> int: return int(self.sample_rate * self.chunk_seconds)

    @property
    def num_classes(self) -> int:   return len(self.classes)


# ─────────────────────────────────────────────────────────────────
#  Fusion config
# ─────────────────────────────────────────────────────────────────

@dataclass
class FusionConfig:
    danger_threshold  : float = 0.55
    warning_threshold : float = 0.35
    use_learned_mlp   : bool  = False    # disabled — no MLP weights trained
    mlp_hidden        : int   = 128
    input_dim         : int   = 19       # 14 video + 5 audio class probs


# ─────────────────────────────────────────────────────────────────
#  Temporal engine config (replaces MIL for inference)
# ─────────────────────────────────────────────────────────────────

@dataclass
class TemporalConfig:
    buffer_size         : int   = 10     # keep last N risk scores
    min_buffer_fill     : int   = 5      # wait until buffer has at least N entries
    high_score_threshold: float = 0.50   # score must exceed this to count as "high"
    min_high_count      : int   = 2      # need at least N "high" scores in buffer
    max_score_threshold : float = 0.80   # AND max score must exceed this


# ─────────────────────────────────────────────────────────────────
#  Alert config  (reads from env vars set in .env)
# ─────────────────────────────────────────────────────────────────

@dataclass
class AlertConfig:
    twilio_sid    : str  = os.getenv("TWILIO_SID",   "")
    twilio_token  : str  = os.getenv("TWILIO_TOKEN", "")
    twilio_from   : str  = os.getenv("TWILIO_FROM",  "")
    alert_to      : str  = os.getenv("ALERT_TO",     "")
    cooldown_secs : int  = 30
    enable_sms    : bool = True
    camera_label  : str  = "SafeZone Camera 1"
    audit_log     : str  = "logs/audit.jsonl"


# ─────────────────────────────────────────────────────────────────
#  Server config
# ─────────────────────────────────────────────────────────────────

@dataclass
class ServerConfig:
    host : str = "0.0.0.0"
    port : int = 8000


# ─────────────────────────────────────────────────────────────────
#  Singletons — import these everywhere
# ─────────────────────────────────────────────────────────────────

PATHS  = Paths()
VCFG   = VideoConfig()
ACFG   = AudioConfig()
FCFG   = FusionConfig()
TCFG   = TemporalConfig()
ALCFG  = AlertConfig()
SCFG   = ServerConfig()
