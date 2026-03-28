# SafeZone Alert System Setup Guide

## Overview

SafeZone now supports email-only alerting.

- 📧 **Email alerts** to your configured Gmail recipient

Alerts are sent with a 30-second cooldown to prevent flooding.

---

## Email Setup (Gmail SMTP)

### Step 1: Enable 2-Step Verification

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** in the left menu
3. Scroll to "How you sign in to Google"
4. Enable **2-Step Verification** if not already enabled

### Step 2: Create an App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select **Mail** and choose a device
3. Google will show a 16-character app password
4. **Copy this password** — you'll need it for the `.env` file

### Step 3: Update `.env`

Edit `.env` in the `safezone_prod` directory:

```env
EMAIL_ENABLED=true
EMAIL_FROM=panditbimlendra10@gmail.com
EMAIL_USERNAME=panditbimlendra10@gmail.com
EMAIL_PASSWORD=your_gmail_app_password_here
ALERT_EMAIL=panditbimendra@gmail.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_SSL=false
EMAIL_USE_TLS=true
ALERT_COOLDOWN=30
```

If you see a Gmail error like `535 Username and Password not accepted`, verify that:

- `EMAIL_PASSWORD` is a 16-character Gmail app password
- 2-Step Verification is enabled on the sender account
- `EMAIL_USERNAME` matches the Gmail account used to generate the app password

### Testing Email

- SafeZone sends email when abnormal activity is detected
- Check the `ALERT_EMAIL` inbox for messages like: "🚨 SafeZone Alert - WARNING Activity Detected"

---

## Alert Levels

A detection can trigger an email alert based on `risk_level`.

| Risk Level | Email |
| ---------- | ----- |
| NORMAL     | ❌    |
| WARNING    | ✅    |
| DANGER     | ✅    |

---

## Email Content Format

When SafeZone detects abnormal activity, you'll receive an alert email with details like:

```
SafeZone AI ALERT
==================================================

TIME: 2024-01-15 14:23:45
RISK LEVEL: WARNING
RISK SCORE: 78.5%

VIDEO DETECTION:
  Activity: Assault Detected
  Confidence: 92%

AUDIO DETECTION:
  Sound: Scream
  Confidence: 85%

CAMERA: SafeZone Camera 1

==================================================
Please take immediate action if needed.
```

---

## Cooldown Period

SafeZone enforces a **30-second cooldown** between consecutive alerts to prevent flooding:

- First alert sent → ✅
- Second alert within 30 seconds → ⏭️ Suppressed
- Alert after 30 seconds → ✅

To change it, update:

```env
ALERT_COOLDOWN=30
```

---

## Troubleshooting

### Email not sending

- **Error:** "Email auth failed — Check EMAIL_FROM and EMAIL_PASSWORD"
  - ✅ Use an app password, not your regular Google password
  - ✅ Ensure 2-Step Verification is enabled
  - ✅ Ensure `EMAIL_FROM` matches the Gmail account used for the app password

- **Error:** "SMTP connection error"
  - ✅ Check internet connectivity
  - ✅ Ensure the sender email is valid and formatted correctly
  - ✅ Ensure `EMAIL_PASSWORD` is a 16-character app password

### `.env` file not loading

- ✅ `.env` must be in the `safezone_prod/` directory
- ✅ No extra spaces around `=` signs
- ✅ Restart the backend after editing `.env`

```bash
cd safezone_prod
python -m pip install python-dotenv
uvicorn backend.main:app --reload
```

---

## Sample `.env` Configuration

```env
EMAIL_ENABLED=true
EMAIL_FROM=panditbimlendra10@gmail.com
EMAIL_USERNAME=panditbimlendra10@gmail.com
EMAIL_PASSWORD=your_gmail_app_password_here
ALERT_EMAIL=panditbimendra@gmail.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_SSL=false
EMAIL_USE_TLS=true
ALERT_COOLDOWN=30
```

---

## Next Steps

1. Update `.env` with your Gmail SMTP credentials
2. Restart the SafeZone backend server
3. Trigger abnormal activity to generate an alert
4. Confirm receipt of the alert email

For help, check `safezone_prod/logs/audit.jsonl` for alert history.

Happy monitoring! 🚨
