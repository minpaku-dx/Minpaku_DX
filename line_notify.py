"""
line_notify.py — LINE通知送信
Flex Messageでゲスト名・物件名付きの承認カードを送信する。
"""
import os
from dotenv import load_dotenv
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    FlexMessage,
    FlexContainer,
)

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
OWNER_USER_ID = os.getenv("LINE_OWNER_USER_ID")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)


def send_line_message(
    pending_id: str,
    booking_id: str,
    guest_message: str,
    ai_reply: str,
    conversation_history: str = "",
    guest_name: str = "",
    property_name: str = "",
):
    """承認/修正ボタン付きFlex Messageをオーナーに送信する"""

    guest_short = guest_message[:150]
    reply_short = ai_reply[:300]
    history_short = conversation_history[:500] if conversation_history else ""

    # ── ヘッダー情報 ──
    header_subtitle = f"予約ID: {booking_id}"
    if guest_name and property_name:
        header_subtitle = f"{guest_name} | {property_name}"
    elif guest_name:
        header_subtitle = guest_name
    elif property_name:
        header_subtitle = property_name

    # ── body コンテンツ ──
    body_contents = []

    # 予約ID（ヘッダーにゲスト名を表示する場合）
    if guest_name or property_name:
        body_contents.append({
            "type": "text",
            "text": f"予約ID: {booking_id}",
            "size": "xxs",
            "color": "#aaaaaa",
        })

    # 直近のやり取り
    if history_short:
        body_contents.extend([
            {
                "type": "separator",
                "margin": "md",
            },
            {
                "type": "text",
                "text": "直近のやり取り",
                "weight": "bold",
                "size": "xs",
                "color": "#999999",
                "margin": "md",
            },
            {
                "type": "text",
                "text": history_short,
                "size": "xxs",
                "color": "#aaaaaa",
                "wrap": True,
                "margin": "sm",
            },
        ])

    # ゲストメッセージ
    body_contents.extend([
        {
            "type": "separator",
            "margin": "md",
        },
        {
            "type": "text",
            "text": "ゲスト",
            "weight": "bold",
            "size": "sm",
            "color": "#555555",
            "margin": "md",
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
            "margin": "md",
        },
    ])

    # AI返信案
    body_contents.extend([
        {
            "type": "text",
            "text": "AI返信案",
            "weight": "bold",
            "size": "sm",
            "color": "#555555",
            "margin": "md",
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
                    "text": "新着ゲストメッセージ",
                    "weight": "bold",
                    "size": "md",
                    "color": "#1a73e8",
                },
                {
                    "type": "text",
                    "text": header_subtitle,
                    "size": "xs",
                    "color": "#555555",
                    "margin": "sm",
                    "weight": "bold",
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
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "承認して送信",
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
                                "label": "修正する",
                                "data": f"action=edit&pending_id={pending_id}",
                            },
                            "style": "secondary",
                            "height": "sm",
                            "margin": "md",
                        },
                    ],
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "スキップ",
                        "data": f"action=skip&pending_id={pending_id}",
                    },
                    "style": "secondary",
                    "color": "#aaaaaa",
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
                        alt_text=f"新着: {guest_name or '予約'+booking_id} からのメッセージ",
                        contents=FlexContainer.from_dict(flex_json),
                    )
                ],
            )
        )


def send_proactive_line_message(
    proactive_id: str,
    booking_id: str,
    trigger_type: str,
    ai_message: str,
    guest_name: str = "",
    property_name: str = "",
    check_in: str = "",
    check_out: str = "",
):
    """プロアクティブメッセージ用のFlex Messageをオーナーに送信する"""

    message_short = ai_message[:400]

    # トリガー別のラベル
    if trigger_type == "pre_checkin":
        title = "チェックイン前ウェルカム"
        title_color = "#06d6a0"
        bg_color = "#f0fff4"
    else:
        title = "チェックアウト後サンキュー"
        title_color = "#7209b7"
        bg_color = "#f8f0ff"

    header_subtitle = f"予約ID: {booking_id}"
    if guest_name and property_name:
        header_subtitle = f"{guest_name} | {property_name}"
    elif guest_name:
        header_subtitle = guest_name

    body_contents = [
        {
            "type": "text",
            "text": f"予約ID: {booking_id}",
            "size": "xxs",
            "color": "#aaaaaa",
        },
    ]

    if check_in and check_out:
        body_contents.append({
            "type": "text",
            "text": f"IN {check_in} → OUT {check_out}",
            "size": "xxs",
            "color": "#aaaaaa",
            "margin": "sm",
        })

    body_contents.extend([
        {
            "type": "separator",
            "margin": "md",
        },
        {
            "type": "text",
            "text": "AIメッセージ案",
            "weight": "bold",
            "size": "sm",
            "color": "#555555",
            "margin": "md",
        },
        {
            "type": "text",
            "text": message_short,
            "size": "sm",
            "wrap": True,
            "margin": "sm",
        },
    ])

    # pending_id に "pro_" プレフィックスを付けてプロアクティブと識別
    prefixed_id = f"pro_{proactive_id}"

    flex_json = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "md",
                    "color": title_color,
                },
                {
                    "type": "text",
                    "text": header_subtitle,
                    "size": "xs",
                    "color": "#555555",
                    "margin": "sm",
                    "weight": "bold",
                },
            ],
            "backgroundColor": bg_color,
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
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "承認して送信",
                                "data": f"action=approve&pending_id={prefixed_id}",
                            },
                            "style": "primary",
                            "color": title_color,
                            "height": "sm",
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "修正する",
                                "data": f"action=edit&pending_id={prefixed_id}",
                            },
                            "style": "secondary",
                            "height": "sm",
                            "margin": "md",
                        },
                    ],
                },
                {
                    "type": "button",
                    "action": {
                        "type": "postback",
                        "label": "スキップ",
                        "data": f"action=skip&pending_id={prefixed_id}",
                    },
                    "style": "secondary",
                    "color": "#aaaaaa",
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
                        alt_text=f"プロアクティブ: {guest_name or '予約'+booking_id}",
                        contents=FlexContainer.from_dict(flex_json),
                    )
                ],
            )
        )
