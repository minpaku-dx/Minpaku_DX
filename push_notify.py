"""
push_notify.py — FCM push notification for mobile app.

Initializes Firebase Admin SDK using FIREBASE_CREDENTIALS env var (JSON string).
Gracefully handles Firebase not being configured — logs warning, doesn't crash.
"""
import os
import json
import logging

from dotenv import load_dotenv
load_dotenv()

import db

logger = logging.getLogger("minpaku-dx.push")

_firebase_available = False
_firebase_app = None

FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "")

if FIREBASE_CREDENTIALS:
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        _firebase_available = True
        logger.info("Firebase Admin SDK initialized")
    except Exception as e:
        logger.warning("Firebase初期化失敗（プッシュ通知が無効）: %s", e)
else:
    logger.warning("FIREBASE_CREDENTIALS が未設定 — プッシュ通知が無効です")


def send_push_notification(property_id: int, message_type: str, data: dict) -> int:
    """
    Send push notification to all devices linked to a property's users.

    Args:
        property_id: The property ID to notify users for
        message_type: Type of notification (e.g., 'new_message', 'proactive')
        data: Dict with notification payload (title, body, etc.)

    Returns: number of successful sends
    """
    if not _firebase_available:
        logger.debug("Firebase未設定 — プッシュ通知スキップ")
        return 0

    from firebase_admin import messaging

    devices = db.get_devices_for_property(property_id)
    if not devices:
        logger.debug("property_id=%d のデバイスなし — プッシュ通知スキップ", property_id)
        return 0

    success_count = 0
    invalid_tokens = []

    for device in devices:
        fcm_token = device["fcm_token"]
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=data.get("title", "民泊DX"),
                    body=data.get("body", ""),
                ),
                data={
                    "type": message_type,
                    "property_id": str(property_id),
                    **{k: str(v) for k, v in data.get("extra", {}).items()},
                },
                token=fcm_token,
            )
            messaging.send(message)
            success_count += 1
        except Exception as e:
            error_str = str(e)
            # Handle invalid/expired tokens
            if "not-registered" in error_str.lower() or "invalid-registration" in error_str.lower() or "registration-token-not-registered" in error_str.lower():
                logger.info("無効なFCMトークンを削除: %s...", fcm_token[:20])
                invalid_tokens.append(fcm_token)
            else:
                logger.error("FCM送信失敗 (token=%s...): %s", fcm_token[:20], e)

    # Cleanup invalid tokens
    for token in invalid_tokens:
        try:
            db.delete_device(token)
        except Exception as e:
            logger.error("デバイス削除失敗: %s", e)

    logger.info("プッシュ通知送信: property_id=%d, 成功=%d/%d", property_id, success_count, len(devices))
    return success_count


def register_device(user_id: str, fcm_token: str, platform: str, app_version: str | None = None) -> None:
    """Register or update a device for push notifications."""
    db.upsert_device(user_id, fcm_token, platform, app_version)
    logger.info("デバイス登録: user=%s, platform=%s", user_id, platform)


def unregister_device(fcm_token: str) -> None:
    """Remove a device from push notifications."""
    db.delete_device(fcm_token)
    logger.info("デバイス解除: token=%s...", fcm_token[:20] if fcm_token else "")
