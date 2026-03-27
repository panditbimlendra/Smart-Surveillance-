"""
SafeZone AI — Alert System
Multi-channel alerts: Email + Twilio SMS/Call with cooldown to prevent flooding.
Gracefully degrades if services are not configured.
"""

from __future__ import annotations
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, Optional

from config import ALCFG, AlertConfig
from utils.logger import get_logger, AuditLogger


class AlertSystem:
    """
    Manages multi-channel alert dispatch (Email + SMS + Call) with cooldown gate.

    maybe_alert() is the only public method you need to call.
    It decides whether to send alerts based on:
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
        self._smtp_server    = "smtp.gmail.com"
        self._smtp_port      = 587

        if cfg.twilio_enabled:
            self._init_twilio()

        if cfg.email_enabled:
            self._init_email()

    # ── Public API ─────────────────────────────────────────────

    def maybe_alert(self, fusion_result: Dict[str, Any]) -> bool:
        """
        Evaluate the fusion result and fire alerts if conditions are met.
        Always writes to the audit log.
        Returns True if any alert was actually sent.
        """
        alerts_sent = []

        if fusion_result.get("should_alert", False):
            now      = time.time()
            elapsed  = now - self._last_alert_ts

            if elapsed >= self.cfg.cooldown_secs:
                # Send email alert
                if self.cfg.email_enabled and self.cfg.email_from and self.cfg.alert_email:
                    email_sent = self._send_email(fusion_result)
                    alerts_sent.append(email_sent)

                # Send SMS alert
                if self.cfg.twilio_enabled and self._twilio_client:
                    sms_sent = self._send_sms(fusion_result)
                    alerts_sent.append(sms_sent)
                    
                    # Also send call alert for high-risk scenarios
                    if fusion_result.get("risk_level") == "DANGER":
                        call_sent = self._send_call(fusion_result)
                        alerts_sent.append(call_sent)

                if any(alerts_sent):
                    self._last_alert_ts = now
            else:
                remaining = self.cfg.cooldown_secs - elapsed
                self._log.debug("Alert suppressed — cooldown %.0fs remaining", remaining)

        self._audit.record(fusion_result, sms_sent=any(alerts_sent) if alerts_sent else False)
        return any(alerts_sent) if alerts_sent else False

    def cooldown_remaining(self) -> float:
        """Seconds left on current cooldown (0 = ready)."""
        return max(0.0, self.cfg.cooldown_secs - (time.time() - self._last_alert_ts))

    # ── Email Alerts ──────────────────────────────────────────

    def _init_email(self) -> None:
        """Initialize email configuration."""
        if not self.cfg.email_from or not self.cfg.email_password:
            self._log.warning("Email credentials not set — Email alerts disabled. Set EMAIL_FROM / EMAIL_PASSWORD env vars.")
            return
        self._log.info("Email alerts enabled for %s", self.cfg.alert_email)

    def _send_email(self, fusion_result: Dict[str, Any]) -> bool:
        """Send email alert with abnormal activity details."""
        if not self.cfg.email_from or not self.cfg.email_password or not self.cfg.alert_email:
            self._log.info("[Email disabled] Would have sent alert to %s", self.cfg.alert_email)
            return False

        try:
            # Build email content
            subject = f"🚨 SafeZone Alert - {fusion_result['risk_level']} Activity Detected"
            
            body_text = self._build_email_body(fusion_result)
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.cfg.email_from
            msg["To"] = self.cfg.alert_email
            
            # Attach plain text version
            msg.attach(MIMEText(body_text, "plain"))
            
            # Send via Gmail SMTP
            with smtplib.SMTP(self._smtp_server, self._smtp_port) as server:
                server.starttls()
                server.login(self.cfg.email_from, self.cfg.email_password)
                server.send_message(msg)
            
            self._log.warning("EMAIL ALERT sent to %s", self.cfg.alert_email)
            return True
            
        except smtplib.SMTPAuthenticationError:
            self._log.error("Email auth failed — Check EMAIL_FROM and EMAIL_PASSWORD. Use Gmail App Password, not regular password.")
            return False
        except Exception as e:
            self._log.error("Email send failed: %s", e)
            return False

    def _build_email_body(self, r: Dict[str, Any]) -> str:
        """Build formatted email body with detection details."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        return f"""
SafeZone AI ALERT
{'='*50}

TIME: {ts}
RISK LEVEL: {r['risk_level']}
RISK SCORE: {r['risk_score']:.1%}

VIDEO DETECTION:
  Activity: {r['top_video']}
  Confidence: {r.get('video_conf', 0):.0%}

AUDIO DETECTION:
  Sound: {r['top_audio']}
  Confidence: {r.get('audio_conf', 0):.0%}

CAMERA: {self.cfg.camera_label}

{'='*50}
Please take immediate action if needed.
        """.strip()

    # ── SMS Alerts (Twilio) ────────────────────────────────────

    def _init_twilio(self) -> None:
        """Initialize Twilio SMS/Call client."""
        if not self.cfg.twilio_sid or not self.cfg.twilio_token:
            self._log.warning("Twilio credentials not set — SMS/Call disabled. Set TWILIO_SID / TWILIO_TOKEN env vars.")
            return
        try:
            from twilio.rest import Client
            self._twilio_client = Client(self.cfg.twilio_sid, self.cfg.twilio_token)
            self._log.info("Twilio client initialised. SMS/Call enabled for %s", self.cfg.alert_phone)
        except ImportError:
            self._log.warning("twilio package not installed — SMS/Call disabled. pip install twilio")
        except Exception as e:
            self._log.warning("Twilio init failed: %s", e)

    def _send_sms(self, fusion_result: Dict[str, Any]) -> bool:
        """Send SMS alert via Twilio."""
        message = self._build_sms_message(fusion_result)
        
        if not self.cfg.twilio_enabled or self._twilio_client is None:
            self._log.info("[SMS disabled] Would have sent to %s: %s", self.cfg.alert_phone, message)
            return False

        try:
            msg = self._twilio_client.messages.create(
                body  = message,
                from_ = self.cfg.twilio_from,
                to    = self.cfg.alert_phone,
            )
            self._log.warning("SMS sent to %s — SID: %s", self.cfg.alert_phone, msg.sid)
            return True
        except Exception as e:
            self._log.error("SMS send failed: %s", e)
            return False

    def _send_call(self, fusion_result: Dict[str, Any]) -> bool:
        """Send automated call alert via Twilio for critical incidents."""
        if not self.cfg.twilio_enabled or self._twilio_client is None or fusion_result.get("risk_level") != "DANGER":
            return False

        try:
            # Create TwiML (Twilio Markup Language) for call
            twiml_message = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">SafeZone Alert. Danger activity detected. {fusion_result['top_video']}. Risk score {fusion_result['risk_score']:.0%}.</Say>
    <Pause length="1"/>
    <Say voice="alice">Abnormal activity at {self.cfg.camera_label}. Please respond immediately.</Say>
</Response>"""
            
            call = self._twilio_client.calls.create(
                url  = twiml_message,  # TwiML instructions
                to   = self.cfg.alert_phone,
                from_= self.cfg.twilio_from,
            )
            self._log.warning("DANGER CALL sent to %s — SID: %s", self.cfg.alert_phone, call.sid)
            return True
        except Exception as e:
            self._log.error("Call send failed: %s", e)
            return False

    def _build_sms_message(self, r: Dict[str, Any]) -> str:
        """Build concise SMS message."""
        ts = time.strftime("%H:%M:%S")
        return (
            f"SAFEZONE ALERT [{self.cfg.camera_label}] @ {ts}\n"
            f"Level: {r['risk_level']}\n"
            f"Risk: {r['risk_score']:.0%}\n"
            f"Video: {r['top_video']}\n"
            f"Audio: {r['top_audio']}"
        )
