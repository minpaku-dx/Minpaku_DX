import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RULES_DIR = Path(__file__).parent / "rules"
AI_MODEL = "gemini-2.5-flash"

_client = None

# Country → language fallback map (when guestLanguage is empty)
_COUNTRY_LANGUAGE_MAP = {
    "FR": "French", "DE": "German", "CN": "Chinese", "TW": "Chinese",
    "KR": "Korean", "ES": "Spanish", "IT": "Italian", "PT": "Portuguese",
    "BR": "Portuguese", "NL": "Dutch", "RU": "Russian", "TH": "Thai",
    "VN": "Vietnamese", "ID": "Indonesian", "PH": "English",
    "US": "English", "GB": "English", "AU": "English", "CA": "English",
    "NZ": "English", "IN": "English", "SG": "English",
}

# Western country codes (for tone adjustment)
_WESTERN_COUNTRIES = {
    "US", "GB", "AU", "CA", "NZ", "IE", "FR", "DE", "IT", "ES",
    "PT", "NL", "BE", "AT", "CH", "SE", "NO", "DK", "FI",
}


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


def _build_cultural_context(guest_country: str, num_child: int, num_adult: int) -> str:
    """ゲストの属性に基づく文化・対応コンテキストを構築する。"""
    lines = []
    country_upper = guest_country.upper() if guest_country else ""

    # Tone guidance based on origin
    if country_upper in _WESTERN_COUNTRIES:
        lines.append("- このゲストは欧米圏からのお客様です。フレンドリーでカジュアル寄りのトーンで対応してください。")
        lines.append("- 日本ならではのユニークな体験（温泉、居酒屋、コンビニ文化など）を積極的に紹介すると喜ばれます。")
        lines.append("- 文化Tipsセクションの情報（靴を脱ぐ、ゴミ分別、電車マナーなど）を自然に織り込んでください。")
    elif country_upper and country_upper not in ("JP", "JAPAN"):
        lines.append("- 海外からのゲストです。丁寧で親切なトーンを維持してください。")

    # Family with children
    if num_child and num_child > 0:
        lines.append(f"- お子様連れ（{num_child}名）のご家族です。子供向けスポット（水族館、動物園、公園）を優先的に紹介してください。")
        lines.append("- 子供の安全に関連する情報（段差、浴槽の注意など）があれば触れてください。")

    # Large group
    if num_adult and num_adult >= 3:
        lines.append(f"- 大人{num_adult}名のグループです。近隣への騒音配慮を丁寧にお願いしてください（押し付けがましくなく）。")

    if not lines:
        return ""
    return "# 文化・属性コンテキスト\n" + "\n".join(lines)


def _build_language_instruction(guest_language: str, guest_country: str, guest_message: str | None = None) -> str:
    """ゲストの言語設定に基づく言語指示を構築する。"""
    # 1. guestLanguage が明示的に設定されている場合
    if guest_language and guest_language.lower() not in ("", "ja", "japanese", "日本語"):
        return (
            f"\n- ゲストの言語は「{guest_language}」です。"
            f"返信全体を必ず{guest_language}で作成してください。"
            "このプロンプトが日本語で書かれているのは参照用です。出力は必ずゲストの言語で行ってください。"
        )

    # 2. guestLanguage が空だが、国籍からの推定が可能な場合
    country_upper = guest_country.upper() if guest_country else ""
    if country_upper and country_upper not in ("JP", "JAPAN", "日本"):
        inferred_lang = _COUNTRY_LANGUAGE_MAP.get(country_upper)
        if inferred_lang:
            return (
                f"\n- ゲストの国籍は{guest_country}です。"
                f"返信全体を必ず{inferred_lang}で作成してください。"
                "このプロンプトが日本語で書かれているのは参照用です。出力は必ずゲストの言語で行ってください。"
            )
        # 国籍はあるがマッピングにない場合は英語フォールバック
        return (
            "\n- ゲストは海外からのお客様です。"
            "返信全体を必ず英語（English）で作成してください。"
            "このプロンプトが日本語で書かれているのは参照用です。出力は必ずゲストの言語で行ってください。"
        )

    # 3. メッセージ内容から判定（generate_reply用）
    if guest_message and not _is_japanese(guest_message):
        return (
            "\n- ゲストのメッセージは日本語以外で書かれています。"
            "ゲストと同じ言語で返信全体を作成してください。"
            "このプロンプトが日本語で書かれているのは参照用です。出力は必ずゲストの言語で行ってください。"
        )

    return ""


def generate_reply(
    guest_message: str,
    property_id: int,
    thread: list[dict],
    booking_info: dict,
    user_settings: dict | None = None,
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

    # 文化・属性コンテキスト
    cultural_context = _build_cultural_context(guest_country, num_child, num_adult)

    # 言語指示
    language_instruction = _build_language_instruction(guest_language, guest_country, guest_message)

    # ユーザー設定からAI署名・トーン
    signature = "民泊スタッフ一同"
    tone_instruction = ""
    if user_settings:
        signature = user_settings.get("ai_signature") or signature
        ai_tone = user_settings.get("ai_tone", "friendly")
        if ai_tone == "formal":
            tone_instruction = "\n- フォーマルで格式高いトーンで返信してください。"
        elif ai_tone == "casual":
            tone_instruction = "\n- カジュアルで親しみやすいトーンで返信してください。敬語は使いつつもフレンドリーに。"

    prompt = f"""あなたはプロの民泊コンシェルジュです。以下の情報をもとに、ゲストへの丁寧な返信案を1つ作成してください。

{rules_section}

# 予約情報
- ゲスト名: {guest_name}
- 物件: {property_name}
- チェックイン: {check_in}
- チェックアウト: {check_out}
{guest_details_text}

{cultural_context}

# これまでの会話
{thread_text}

# ゲストの最新メッセージ
{guest_message}

【返信のルール】
- まずゲストの名前で呼びかけてから本文を始める（例: 「{guest_name}様」）
- 温かみのある「おもてなし」の精神で対応する：ゲストが聞いていないことでも、1つ役立つ情報を先回りして提供する
- 物件ルールに基づいた正確な情報を含める（ルールに【要確認】とある情報は使わない）
- 署名は「{signature}」とする
- 返信案のみを出力する（前置き・説明文は不要）{tone_instruction}{language_instruction}
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
    user_settings: dict | None = None,
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

    # 文化・属性コンテキスト
    cultural_context = _build_cultural_context(guest_country, num_child, num_adult)

    # 言語指示
    language_instruction = _build_language_instruction(guest_language, guest_country)

    # ユーザー設定からAI署名・トーン
    signature = "民泊スタッフ一同"
    tone_instruction = ""
    if user_settings:
        signature = user_settings.get("ai_signature") or signature
        ai_tone = user_settings.get("ai_tone", "friendly")
        if ai_tone == "formal":
            tone_instruction = "\n- フォーマルで格式高いトーンで作成してください。"
        elif ai_tone == "casual":
            tone_instruction = "\n- カジュアルで親しみやすいトーンで作成してください。敬語は使いつつもフレンドリーに。"

    if trigger_type == "pre_checkin":
        purpose = f"""チェックイン2日前のウェルカムメッセージを作成してください。

【メッセージに含めるべき内容】
- まず「{guest_name}様」と名前で呼びかける温かい歓迎の挨拶
- チェックイン日時の確認
- チェックイン方法の簡潔な案内（物件ルールに記載があれば。【要確認】の情報は使わない）
- ゲストの属性に合わせたおすすめスポットや情報（文化・属性コンテキストを参考に）
- 質問があればいつでも連絡してくださいという一言

【注意】
- 押し付けがましくならないこと
- 長すぎないこと（200〜400文字程度）
- ゲストがまだ質問していないことに先回りして答える「おもてなし」の精神"""
    else:  # post_checkout
        purpose = f"""チェックアウト翌日のサンキューメッセージを作成してください。

【メッセージに含めるべき内容】
- 「{guest_name}様」と名前で呼びかけ、滞在への感謝
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

{cultural_context}

# タスク
{purpose}

【共通ルール】
- 温かみのある「おもてなし」の精神で対応する
- 物件ルールに【要確認】とある情報は使わない
- 署名は「{signature}」とする
- メッセージ本文のみを出力する（前置き・説明文は不要）{tone_instruction}{language_instruction}
"""

    client = _get_client()
    response = client.models.generate_content(
        model=AI_MODEL,
        contents=prompt,
    )
    return response.text
