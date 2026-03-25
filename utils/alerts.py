"""
SafeZone AI — Alert System
Twilio SMS dispatch with cooldown to prevent SMS flooding.
Gracefully degrades if Twilio is not configured.
"""

from __future__ import annotations
import time
from typing import Any, Dict, Optional

from config import ALCFG, AlertConfig
from utils.logger import get_logger, AuditLogger


class AlertSystem:
    """
    Manages alert dispatch with cooldown gate.

    maybe_alert() is the only public method you need to call.
    It decides whether to send an SMS based on:
      (a) fusion_result["should_alert"] is True
      (b) cooldown period has elapsed since last alert

    The audit log is written on every call regardless of cooldown.
    """

    def __init__(self, cfg: AlertConfig = ALCFG, camera_id: str = "Camera 1"):
        self.cfg             = cfg
        self._last_alert_ts  = 0.0
        self._log            = get_logger("safezone.alert")
        self._audit          = AuditLogger(cfg.audit_log if hasattr(cfg, "audit_log") else "logs/audit.jsonl", camera_id)
        self._twilio_client  = None

        if cfg.enable_sms:
            self._init_twilio()

    # ── Public API ─────────────────────────────────────────────

    def maybe_alert(self, fusion_result: Dict[str, Any]) -> bool:
        """
        Evaluate the fusion result and fire an SMS if conditions are met.
        Always writes to the audit log.
        Returns True if an SMS was actually sent.
        """
        sms_sent = False

        if fusion_result.get("should_alert", False):
            now      = time.time()
            elapsed  = now - self._last_alert_ts

            if elapsed >= self.cfg.cooldown_secs:
                sms_sent = self._send(fusion_result)
                if sms_sent:
                    self._last_alert_ts = now
            else:
                remaining = self.cfg.cooldown_secs - elapsed
                self._log.debug("Alert suppressed — cooldown %.0fs remaining", remaining)

        self._audit.record(fusion_result, sms_sent=sms_sent)
        return sms_sent

    def cooldown_remaining(self) -> float:
        """Seconds left on current cooldown (0 = ready)."""
        return max(0.0, self.cfg.cooldown_secs - (time.time() - self._last_alert_ts))

    # ── Private helpers ────────────────────────────────────────

    def _init_twilio(self) -> None:
        if not self.cfg.twilio_sid or not self.cfg.twilio_token:
            self._log.warning("Twilio credentials not set — SMS disabled. Set TWILIO_SID / TWILIO_TOKEN env vars.")
            return
        try:
            from twilio.rest import Client
            self._twilio_client = Client(self.cfg.twilio_sid, self.cfg.twilio_token)
            self._log.info("Twilio client initialised.")
        except ImportError:
            self._log.warning("twilio package not installed — SMS disabled. pip install twilio")
        except Exception as e:
            self._log.warning("Twilio init failed: %s", e)

    def _send(self, fusion_result: Dict[str, Any]) -> bool:
        message = self._build_message(fusion_result)
        self._log.warning("ALERT TRIGGER: %s", message.replace("\n", " | "))

        if not self.cfg.enable_sms or self._twilio_client is None:
            self._log.info("[SMS disabled] Would have sent: %s", message)
            return False

        try:
            msg = self._twilio_client.messages.create(
                body  = message,
                from_ = self.cfg.twilio_from,
                to    = self.cfg.alert_to,
            )
            self._log.info("SMS sent — SID: %s", msg.sid)
            return True
        except Exception as e:
            self._log.error("SMS send failed: %s", e)
            return False

    def _build_message(self, r: Dict[str, Any]) -> str:
        ts = time.strftime("%H:%M:%S")
        return (
            f"SAFEZONE ALERT [{self.cfg.camera_label}] @ {ts}\n"
            f"Level : {r['risk_level']}\n"
            f"Risk  : {r['risk_score']:.1%}\n"
            f"Video : {r['top_video']} ({r.get('video_conf', 0):.0%})\n"
            f"Audio : {r['top_audio']} ({r.get('audio_conf', 0):.0%})"
        )
