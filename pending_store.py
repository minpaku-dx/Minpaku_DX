"""
pending_store.py — pending.json の読み書きを一元管理
ai_reply.py と line_webhook.py から共通利用する。
"""
import json
import os

PENDING_FILE = os.path.join(os.path.dirname(__file__), "pending.json")


def load_pending() -> dict:
    """pending.json を読み込んで返す。ファイルがなければ空dictを返す。"""
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_pending(data: dict) -> None:
    """pending.json にデータを書き込む。"""
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
