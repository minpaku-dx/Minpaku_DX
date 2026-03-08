import os
from dotenv import load_dotenv
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
)

load_dotenv()

# ===== LINE 設定 =====
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OWNER_USER_ID = os.getenv("LINE_OWNER_USER_ID")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)


def send_line_message(pending_id: str, booking_id: str, guest_message: str, ai_reply: str, conversation_history: str = ""):
    """承認/修正ボタン付きFlex Messageをオーナーに送信する（会話履歴付き）"""

    # ゲストメッセージとAI返信案を表示用に短縮
    guest_short = guest_message[:150].replace('"', '\\"')
    reply_short = ai_reply[:300].replace('"', '\\"')
    history_short = conversation_history[:500] if conversation_history else ""

    # ── body コンテンツを組み立てる ──
    body_contents = []

    # 📜 直近のやり取り（会話履歴がある場合のみ表示）
    if history_short:
        body_contents.extend([
            {
                "type": "text",
                "text": "📜 直近のやり取り",
                "weight": "bold",
                "size": "xs",
                "color": "#999999",
            },
            {
                "type": "text",
                "text": history_short,
                "size": "xxs",
                "color": "#aaaaaa",
                "wrap": True,
                "margin": "sm",
            },
            {
                "type": "separator",
                "margin": "lg",
            },
        ])

    # 【ゲスト】メッセージ
    body_contents.extend([
        {
            "type": "text",
            "text": "【ゲスト】",
            "weight": "bold",
            "size": "sm",
            "color": "#555555",
            "margin": "lg" if history_short else "none",
        },
        {
            "type": "text",
            "text": guest_short,
            "size": "sm",
            "wrap": True,
            "margin": "sm",
        },
        {
            "type": "separator",
            "margin": "lg",
        },
    ])

    # 【AI返信案】
    body_contents.extend([
        {
            "type": "text",
            "text": "【AI返信案】",
            "weight": "bold",
            "size": "sm",
            "color": "#555555",
            "margin": "lg",
        },
        {
            "type": "text",
            "text": reply_short,
            "size": "sm",
            "wrap": True,
            "margin": "sm",
        },
    ])

    flex_json = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📩 新着ゲストメッセージ",
                    "weight": "bold",
                    "size": "md",
                    "color": "#1a73e8",
                },
                {
                    "type": "text",
                    "text": f"予約ID: {booking_id}",
                    "size": "xs",
                    "color": "#888888",
                    "margin": "sm",
                },
            ],
            "backgroundColor": "#f0f6ff",
            "paddingAll": "15px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "paddingAll": "15px",
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "✅ 承認して送信",
                        "data": f"action=approve&pending_id={pending_id}",
                    },
                    "style": "primary",
                    "color": "#1a73e8",
                    "height": "sm",
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "✏️ 修正する",
                        "data": f"action=edit&pending_id={pending_id}",
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "md",
                },
            ],
            "paddingAll": "15px",
        },
    }

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=OWNER_USER_ID,
                messages=[
                    FlexMessage(
                        alt_text=f"📩 予約ID:{booking_id} のAI返信案が届きました",
                        contents=FlexContainer.from_dict(flex_json),
                    )
                ],
            )
        )


def send_line_text(text: str):
    """シンプルなテキストメッセージをオーナーに送信する"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=OWNER_USER_ID,
                messages=[TextMessage(text=text)],
            )
        )
