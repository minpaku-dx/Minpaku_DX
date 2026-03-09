"""
main.py — CLIエントリーポイント
DBからdraft_readyメッセージを表示し、承認/編集/スキップを行う。
データの取得・AI生成は sync_service.py が担当。
"""
from cli import run_session


if __name__ == "__main__":
    print("\n  Minpaku DX — CLI承認ツール")
    print("  (メッセージ取得・AI生成は sync_service.py が自動実行します)\n")
    run_session()
