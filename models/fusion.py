"""
SafeZone AI — Fusion Engine
safezone_ai/models/fusion.py

Combines video predictions and audio predictions into a single risk score.

Two-stage fusion:
  1. Rule-based score  : weighted sum of top video + top audio class scores
                         using CLASS_RISK_TIER weights
  2. Learned MLP score : small MLP trained on (video_probs + audio_probs)
                         → risk_score (optional, only used if weights exist)

  Final risk_score = 0.6 × rule_score + 0.4 × mlp_score (if MLP available)
                   = rule_score (if no MLP weights)

Risk level thresholds (from FusionConfig):
  risk_score ≥ danger_threshold  → DANGER
  risk_score ≥ warning_threshold → WARNING
  else                           → SAFE
"""

from __future__ import annotations
import os
from typing import Dict, Optional

import numpy as np
import torch
import torch.nn as nn

from config import VCFG, ACFG, FCFG, TIER_SCORE, FusionConfig
from utils.logger import get_logger

logger = get_logger("safezone.fusion")


# ─────────────────────────────────────────────────────────────
#  Small MLP for learned fusion
# ─────────────────────────────────────────────────────────────

class FusionMLP(nn.Module):
    """
    Tiny MLP: (14 video probs + 5 audio probs) → risk_score scalar.
    Trained separately after both video and audio models are ready.
    """

    def __init__(self, input_dim: int = 19, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, input_dim) → (B, 1) risk score in [0, 1]."""
        return self.net(x)


# ─────────────────────────────────────────────────────────────
#  Fusion Engine
# ─────────────────────────────────────────────────────────────

class FusionEngine:
    """
    Fuses video and audio predictions into a final risk assessment.

    Usage:
        engine = FusionEngine(FCFG, weights_path="/path/to/fusion_mlp.pth")
        result = engine.fuse(video_preds, audio_preds)
        # result: {risk_score, risk_level, top_video, top_audio, should_alert, ...}
    """

    def __init__(self, cfg: FusionConfig = FCFG, weights_path: Optional[str] = None):
        self.cfg  = cfg
        self._mlp : Optional[FusionMLP] = None

        if cfg.use_learned_mlp and weights_path and os.path.exists(weights_path):
            try:
                self._mlp = FusionMLP(cfg.input_dim, cfg.mlp_hidden)
                state     = torch.load(weights_path, map_location="cpu")
                if "state_dict" in state:
                    state = state["state_dict"]
                self._mlp.load_state_dict(state)
                self._mlp.eval()
                logger.info("Fusion MLP loaded: %s", weights_path)
            except Exception as e:
                logger.warning("Could not load Fusion MLP: %s — using rule-based only", e)
                self._mlp = None

    def fuse(
        self,
        video_preds : Dict[str, float],
        audio_preds : Dict[str, float],
    ) -> Dict:
        """
        Args:
            video_preds : {class_name: probability}  (14 UCF-Crime classes)
            audio_preds : {class_name: probability}  (5 audio classes)

        Returns dict with keys:
            risk_score, risk_level, top_video, video_conf,
            top_audio, audio_conf, rule_score, mlp_score,
            should_alert, video_preds, audio_preds
        """
        top_video, video_conf = self._top(video_preds)
        top_audio, audio_conf = self._top(audio_preds)

        rule_score = self._rule_score(video_preds, audio_preds, top_video, top_audio)
        mlp_score  = None

        if self._mlp is not None:
            mlp_score  = self._mlp_score(video_preds, audio_preds)
            risk_score = 0.6 * rule_score + 0.4 * mlp_score
        else:
            risk_score = rule_score

        risk_level   = self._classify(risk_score)
        should_alert = risk_level == "DANGER"

        return {
            "risk_score"  : round(float(risk_score),  4),
            "risk_level"  : risk_level,
            "top_video"   : top_video,
            "video_conf"  : round(float(video_conf),  4),
            "top_audio"   : top_audio,
            "audio_conf"  : round(float(audio_conf),  4),
            "rule_score"  : round(float(rule_score),  4),
            "mlp_score"   : round(float(mlp_score), 4) if mlp_score is not None else None,
            "should_alert": should_alert,
            "video_preds" : video_preds,
            "audio_preds" : audio_preds,
        }

    # ── Private helpers ────────────────────────────────────────

    @staticmethod
    def _top(preds: Dict[str, float]) -> tuple[str, float]:
        if not preds:
            return "unknown", 0.0
        top = max(preds, key=preds.get)
        return top, preds[top]

    def _rule_score(
        self,
        video_preds : Dict[str, float],
        audio_preds : Dict[str, float],
        top_video   : str,
        top_audio   : str,
    ) -> float:
        """
        Weighted combination:
          60% video tier score (TIER_SCORE × top_video_conf)
          40% audio tier score (audio class weight × top_audio_conf)
        """
        audio_tier_weights = {
            "normal"     : 0.00,
            "scream"     : 0.65,
            "explosion"  : 0.90,
            "glass_break": 0.70,
            "gunshot"    : 0.90,
        }

        video_tier  = TIER_SCORE.get(
            __import__("config").CLASS_RISK_TIER.get(top_video, "NONE"), 0.0
        )
        video_score = video_tier * video_preds.get(top_video, 0.0)

        audio_tier  = audio_tier_weights.get(top_audio, 0.0)
        audio_score = audio_tier * audio_preds.get(top_audio, 0.0)

        video_is_neutral = (
            top_video == "normal"
            and float(video_preds.get("normal", 0.0)) >= 0.999
        )
        audio_is_neutral = (
            top_audio == "normal"
            and float(audio_preds.get("normal", 0.0)) >= 0.999
        )

        # If one modality is synthetic / unavailable, let the real modality
        # drive the decision instead of permanently down-weighting it.
        if video_is_neutral and not audio_is_neutral:
            return audio_score
        if audio_is_neutral and not video_is_neutral:
            return video_score

        return 0.6 * video_score + 0.4 * audio_score

    def _mlp_score(
        self,
        video_preds : Dict[str, float],
        audio_preds : Dict[str, float],
    ) -> float:
        from config import UCF_CLASSES, AUDIO_CLASSES
        v_vec = np.array([video_preds.get(c, 0.0) for c in UCF_CLASSES], dtype=np.float32)
        a_vec = np.array([audio_preds.get(c, 0.0) for c in AUDIO_CLASSES], dtype=np.float32)
        x     = torch.from_numpy(np.concatenate([v_vec, a_vec])).unsqueeze(0)
        with torch.no_grad():
            return float(self._mlp(x).item())

    def _classify(self, score: float) -> str:
        if score >= self.cfg.danger_threshold:
            return "DANGER"
        elif score >= self.cfg.warning_threshold:
            return "WARNING"
        return "SAFE"
