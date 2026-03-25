"""
SafeZone AI logging utilities.
  AppLogger  : human-readable console + rotating file
  AuditLogger: append-only JSONL event trail
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict


class SafeConsoleHandler(logging.StreamHandler):
    """Console handler that tolerates non-UTF encodings on Windows."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            stream = self.stream
            encoding = getattr(stream, "encoding", None) or "utf-8"
            safe_msg = msg.encode(encoding, errors="replace").decode(encoding, errors="replace")
            stream.write(safe_msg + self.terminator)
            self.flush()


def get_logger(name: str, log_file: str = "logs/safezone.log") -> logging.Logger:
    """Named logger with console INFO+ and file DEBUG+ output."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)-28s  %(message)s",
        datefmt="%H:%M:%S",
    )

    ch = SafeConsoleHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


class AuditLogger:
    """
    Append-only JSONL audit trail.
    Every alert event is written here for evidence, review, and retraining.
    """

    def __init__(self, audit_file: str = "logs/audit.jsonl", camera: str = "Camera 1"):
        Path(audit_file).parent.mkdir(parents=True, exist_ok=True)
        self._file = audit_file
        self._camera = camera
        self._log = get_logger("safezone.audit")

    def record(self, fusion_result: Dict[str, Any], sms_sent: bool = False) -> None:
        entry = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "camera": self._camera,
            "risk_level": fusion_result.get("risk_level", ""),
            "risk_score": round(float(fusion_result.get("risk_score", 0.0)), 4),
            "top_video": fusion_result.get("top_video", ""),
            "video_conf": round(float(fusion_result.get("video_conf", 0.0)), 4),
            "top_audio": fusion_result.get("top_audio", ""),
            "audio_conf": round(float(fusion_result.get("audio_conf", 0.0)), 4),
            "sms_sent": sms_sent,
        }
        with open(self._file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        self._log.info(
            "AUDIT %s risk=%.3f  video=%s(%.2f)  audio=%s(%.2f)  sms=%s",
            entry["risk_level"],
            entry["risk_score"],
            entry["top_video"],
            entry["video_conf"],
            entry["top_audio"],
            entry["audio_conf"],
            sms_sent,
        )
