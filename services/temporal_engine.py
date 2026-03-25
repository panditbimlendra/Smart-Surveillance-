"""
SafeZone AI — Temporal Decision Engine
=========================================
Replaces MIL aggregator for live CCTV inference.

Why this instead of MIL:
  The SlowFast model was trained as a clip-level classifier (one 32-frame
  clip → one prediction), NOT with MIL ranking loss. True MIL needs a model
  trained to rank clips within a bag — we don't have that.

  Instead, we buffer the last N risk_scores from the FusionEngine and
  apply production-grade decision logic:
    1. Persistence check : at least K of the last N scores exceed a threshold
    2. Magnitude check   : the maximum score in the buffer is high enough
  Both conditions must hold before firing an alert.

  This gives us:
    ✓ False positive suppression  (one camera shake won't fire an alert)
    ✓ Temporal context            (anomaly must persist, not be a single spike)
    ✓ Short anomaly detection     (buffer is small enough to catch 1–2 sec events)
    ✓ No retraining required      (pure post-processing logic)

Usage:
    engine = TemporalEngine()
    engine.update(0.62)
    engine.update(0.75)
    is_anomaly, confidence = engine.decision()
"""

from __future__ import annotations
from collections import deque
from typing import Tuple

import numpy as np

from config import TCFG, TemporalConfig
from utils.logger import get_logger

logger = get_logger("safezone.temporal")


class TemporalEngine:
    """
    Rolling buffer of risk scores with production-grade decision logic.

    Parameters (all from TemporalConfig):
        buffer_size          : keep last N scores  (default 10)
        min_buffer_fill      : wait until buffer has ≥ K entries (default 5)
        high_score_threshold : score must exceed this to count as "high" (default 0.50)
        min_high_count       : need ≥ N "high" scores in buffer (default 2)
        max_score_threshold  : AND the max score must exceed this (default 0.80)
    """

    def __init__(self, cfg: TemporalConfig = TCFG):
        self.cfg     = cfg
        self._buffer : deque = deque(maxlen=cfg.buffer_size)
        logger.debug(
            "TemporalEngine init — buffer=%d, min_fill=%d, "
            "high_thresh=%.2f, min_high=%d, max_thresh=%.2f",
            cfg.buffer_size, cfg.min_buffer_fill,
            cfg.high_score_threshold, cfg.min_high_count,
            cfg.max_score_threshold,
        )

    # ── Public API ─────────────────────────────────────────────

    def update(self, risk_score: float) -> None:
        """
        Add a new risk score to the rolling buffer.

        Args:
            risk_score : float in [0, 1] from FusionEngine
        """
        self._buffer.append(float(np.clip(risk_score, 0.0, 1.0)))

    def decision(self) -> Tuple[bool, float]:
        """
        Evaluate whether an anomaly alert should fire.

        Returns:
            (is_anomaly, confidence)
            is_anomaly  : True  → fire alert
            confidence  : max score in buffer (use for alert message)
        """
        if len(self._buffer) < self.cfg.min_buffer_fill:
            # Not enough data yet — wait
            return False, 0.0

        scores     = np.array(self._buffer)
        max_score  = float(scores.max())
        high_count = int(np.sum(scores > self.cfg.high_score_threshold))

        is_anomaly = (
            max_score  >= self.cfg.max_score_threshold
            and high_count >= self.cfg.min_high_count
        )

        if is_anomaly:
            logger.warning(
                "TemporalEngine → ANOMALY  max=%.3f  high_count=%d/%d  buffer=%s",
                max_score, high_count, len(self._buffer),
                [f"{s:.2f}" for s in scores],
            )

        return is_anomaly, max_score

    def reset(self) -> None:
        """Clear the buffer. Call after a camera reconnect or scene change."""
        self._buffer.clear()
        logger.debug("TemporalEngine buffer reset.")

    @property
    def buffer_fill(self) -> int:
        return len(self._buffer)

    @property
    def is_warmed_up(self) -> bool:
        return len(self._buffer) >= self.cfg.min_buffer_fill

    def summary(self) -> dict:
        """Return current buffer stats for debugging / status endpoints."""
        if not self._buffer:
            return {"fill": 0, "max": 0.0, "mean": 0.0, "high_count": 0}
        scores = np.array(self._buffer)
        return {
            "fill"       : len(self._buffer),
            "max"        : round(float(scores.max()), 4),
            "mean"       : round(float(scores.mean()), 4),
            "high_count" : int(np.sum(scores > self.cfg.high_score_threshold)),
        }
