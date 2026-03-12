import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RULES_DIR = Path(__file__).parent / "rules"
AI_MODEL = "gemini-2.5-flash"

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


def _is_japanese(text: str) -> bool:
    """テキストに日本語文字（ひらがな・カタカナ・漢字）が含まれるか判定する。"""
    for ch in text:
        if '\u3040' <= ch <= '\u309F':  # ひらがな
            return True
        if '\u30A0' <= ch <= '\u30FF':  # カタカナ
            return True
        if '\u4E00' <= ch <= '\u9FFF':  # CJK漢字
            return True
    return False


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
    num_adult = booking_info.get("numAdult", 0)
    num_child = booking_info.get("numChild", 0)
    guest_country = booking_info.get("guestCountry", "")
    guest_language = booking_info.get("guestLanguage", "")
    guest_arrival_time = booking_info.get("guestArrivalTime", "")
    guest_comments = booking_info.get("guestComments", "")

    rules_section = f"# 物件ルール\n{rules}" if rules else "# 物件ルール\n（ルールファイルなし）"

    # ゲスト属性セクション
    guest_details = []
    if num_adult or num_child:
        guest_details.append(f"- 人数: 大人{num_adult}名" + (f"、子供{num_child}名" if num_child else ""))
    if guest_country:
        guest_details.append(f"- 国籍: {guest_country}")
    if guest_arrival_time:
        guest_details.append(f"- 到着予定時間: {guest_arrival_time}")
    if guest_comments:
        guest_details.append(f"- ゲストからの備考: {guest_comments}")
    guest_details_text = "\n".join(guest_details)

    # 言語自動検出: guest_languageがあればそれを優先、なければゲストメッセージから判定
    language_instruction = ""
    if guest_language and guest_language.lower() not in ("", "ja", "japanese", "日本語"):
        language_instruction = f"\n- ゲストの言語は「{guest_language}」です。返信は{guest_language}で作成してください。"
    elif not _is_japanese(guest_message):
        language_instruction = "\n- ゲストのメッセージは日本語以外で書かれています。ゲストと同じ言語で返信してください。"

    prompt = f"""あなたはプロの民泊コンシェルジュです。以下の情報をもとに、ゲストへの丁寧な返信案を1つ作成してください。

{rules_section}

# 予約情報
- ゲスト名: {guest_name}
- 物件: {property_name}
- チェックイン: {check_in}
- チェックアウト: {check_out}
{guest_details_text}

# これまでの会話
{thread_text}

# ゲストの最新メッセージ
{guest_message}

【返信のルール】
- 敬語・丁寧語を使う
- 温かみのある表現にする
- 物件ルールに基づいた正確な情報を含める
- 署名は「民泊スタッフ一同」とする
- 返信案のみを出力する（前置き・説明文は不要）{language_instruction}
"""

    client = _get_client()
    response = client.models.generate_content(
        model=AI_MODEL,
        contents=prompt,
    )
    return response.text


def generate_proactive_message(
    trigger_type: str,
    booking_info: dict,
    property_id: int,
) -> str:
    """プロアクティブメッセージ（ウェルカム/サンキュー）のテキストを返す。"""
    rules = _load_property_rules(property_id)

    guest_name = booking_info.get("guestName", "ゲスト様")
    check_in = booking_info.get("checkIn", "不明")
    check_out = booking_info.get("checkOut", "不明")
    property_name = booking_info.get("propertyName", "")
    num_adult = booking_info.get("numAdult", 0)
    num_child = booking_info.get("numChild", 0)
    guest_country = booking_info.get("guestCountry", "")
    guest_language = booking_info.get("guestLanguage", "")
    guest_comments = booking_info.get("guestComments", "")

    rules_section = f"# 物件ルール\n{rules}" if rules else "# 物件ルール\n（ルールファイルなし）"

    guest_details = []
    if num_adult or num_child:
        guest_details.append(f"- 人数: 大人{num_adult}名" + (f"、子供{num_child}名" if num_child else ""))
    if guest_country:
        guest_details.append(f"- 国籍: {guest_country}")
    if guest_comments:
        guest_details.append(f"- ゲストからの備考: {guest_comments}")
    guest_details_text = "\n".join(guest_details)

    # 言語判定
    language_instruction = ""
    if guest_language and guest_language.lower() not in ("", "ja", "japanese", "日本語"):
        language_instruction = f"\n- ゲストの言語は「{guest_language}」です。メッセージは{guest_language}で作成してください。"
    elif guest_country and guest_country.lower() not in ("", "jp", "japan", "日本"):
        language_instruction = "\n- ゲストは海外からのお客様です。メッセージは英語で作成してください。"

    if trigger_type == "pre_checkin":
        purpose = f"""チェックイン2日前のウェルカムメッセージを作成してください。

【メッセージに含めるべき内容】
- 温かい歓迎の挨拶
- チェックイン日時の確認
- チェックイン方法の簡潔な案内（物件ルールに記載があれば）
- ゲストの属性に合わせたおすすめスポットや情報（国籍・家族構成を考慮）
- 質問があればいつでも連絡してくださいという一言

【注意】
- 押し付けがましくならないこと
- 長すぎないこと（200〜400文字程度）
- ゲストがまだ質問していないことに先回りして答える「おもてなし」の精神"""
    else:  # post_checkout
        purpose = f"""チェックアウト翌日のサンキューメッセージを作成してください。

【メッセージに含めるべき内容】
- 滞在への感謝
- 旅の安全を祈る一言
- 「レビューを書いていただけると嬉しいです」というさりげないお願い
- また機会があればぜひという一言

【注意】
- レビュー依頼は押し付けがましくしない
- 短く温かいメッセージ（100〜200文字程度）
- ゲストとの良い思い出で終わる印象にする"""

    prompt = f"""あなたはプロの民泊コンシェルジュです。以下の情報をもとに、ゲストへのメッセージを作成してください。

{rules_section}

# 予約情報
- ゲスト名: {guest_name}
- 物件: {property_name}
- チェックイン: {check_in}
- チェックアウト: {check_out}
{guest_details_text}

# タスク
{purpose}

【共通ルール】
- 敬語・丁寧語を使う
- 温かみのある表現にする
- 署名は「民泊スタッフ一同」とする
- メッセージ本文のみを出力する（前置き・説明文は不要）{language_instruction}
"""

    client = _get_client()
    response = client.models.generate_content(
        model=AI_MODEL,
        contents=prompt,
    )
    return response.text
