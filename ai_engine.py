import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RULES_DIR = Path(__file__).parent / "rules"

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _load_property_rules(property_id: int) -> str:
    """物件IDに対応するルールファイルを読み込む。見つからない場合は空文字。"""
    rules_file = RULES_DIR / f"property_{property_id}.md"
    if rules_file.exists():
        return rules_file.read_text(encoding="utf-8")
    return ""


def _format_thread(thread: list[dict]) -> str:
    """会話スレッドを人間が読みやすい形式に変換する。"""
    if not thread:
        return "（会話履歴なし）"
    lines = []
    for m in thread:
        sender = "ゲスト" if m.get("source") == "guest" else "ホスト"
        lines.append(f"{sender}: {m.get('message', '')}")
    return "\n".join(lines)


def generate_reply(
    guest_message: str,
    property_id: int,
    thread: list[dict],
    booking_info: dict,
) -> str:
    """AI返信案のテキストを返す。"""
    rules = _load_property_rules(property_id)
    thread_text = _format_thread(thread)

    guest_name = booking_info.get("guestName", "ゲスト様")
    check_in = booking_info.get("checkIn", "不明")
    check_out = booking_info.get("checkOut", "不明")
    property_name = booking_info.get("propertyName", "")

    rules_section = f"# 物件ルール\n{rules}" if rules else "# 物件ルール\n（ルールファイルなし）"

    prompt = f"""あなたはプロの民泊コンシェルジュです。以下の情報をもとに、ゲストへの丁寧な返信案を1つ作成してください。

{rules_section}

# 予約情報
- ゲスト名: {guest_name}
- 物件: {property_name}
- チェックイン: {check_in}
- チェックアウト: {check_out}

# これまでの会話
{thread_text}

# ゲストの最新メッセージ
{guest_message}

【返信のルール】
- 敬語・丁寧語を使う
- 温かみのある表現にする
- 物件ルールに基づいた正確な情報を含める
- 署名は「民泊スタッフ一同」とする
- 返信案のみを出力する（前置き・説明文は不要）
"""

    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=prompt,
    )
    return response.text
