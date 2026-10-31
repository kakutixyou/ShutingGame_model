#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/to_model/main.py
コンソールからのCLI実行 (`python -m to_model.main` / `to-model`) および
ローカルHTTP推論サーバー (`--serve`) の両方を担うエントリーポイント。
本体 (ToModelHandler) から直接 import しても、サブプロセス/HTTP経由でも呼び出し可能。
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

from to_model.video.url_video_analyzer import URLVideoAndSongAnalyzer
from to_model.reasoning.jp_nlu_memo import JapaneseExperienceMemoEngine
from to_model.malware.hex_viewer import HexViewer
from to_model.reasoning.decision_policy import DecisionPolicy


class ToModelUnifiedEngine:
    """本体 (ToModelHandler) または CLI から呼び出される統合ファサード"""

    def __init__(self) -> None:
        self.url_analyzer = URLVideoAndSongAnalyzer()
        self.memo_engine = JapaneseExperienceMemoEngine()
        self.hex_viewer = HexViewer()
        self.policy = DecisionPolicy()

    def run(
        self,
        message: str = "",
        mode: Optional[str] = None,
        action_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        チャット入力またはフロントエンド (.tsx) の `onOptionSelect` アクションを受け取り、
        AIChatMessageList.tsx がそのまま描画できる構造化JSONを返す。
        """
        # 1. フロントエンド (.tsx) のボタン操作 (`onOptionSelect`) からのコールバック処理
        if isinstance(action_payload, dict) and action_payload.get("action"):
            act = str(action_payload["action"])
            if act == "analyze_url":
                target_url = str(action_payload.get("url") or "https://www.youtube.com/watch?v=shmup_boss_01")
                res = self.url_analyzer.analyze_url(
                    target_url,
                    custom_lexicon=action_payload.get("custom_lexicon"),
                    silence_threshold_sec=float(action_payload.get("silence_threshold_sec", 0.8)),
                )
                return {
                    "response_type": "to_model_studio",
                    "active_page": "video",
                    "message": f"🎬 URL解析完了: {res['genre']['primary']} (話者 {res['speaker_summary']['total_speakers_count']}人 / 全{len(res['segments'])}セグメント)",
                    "data": {"video_analysis": res},
                }

        # 2. 自動モード判定（明示指定がない場合）
        lower = message.lower()
        resolved_mode = mode
        if not resolved_mode:
            if any(k in lower or k in message for k in ("dos mode", "keylog", "synflood", "portscanner", "マルウェア", "キーロガー")):
                resolved_mode = "security"
            elif any(k in lower or k in message for k in ("ブラック企業", "残業", "連勤", "大変だった", "コメントもjson", "体験談")):
                resolved_mode = "memo"
            else:
                resolved_mode = "video"

        # 3. モード別のモデル実行
        if resolved_mode == "security":
            sec_report = self.hex_viewer.inspect_binary_or_strings(message)
            decisions = self.policy.select_defense_policy(sec_report)
            return {
                "response_type": "to_model_studio",
                "active_page": "security",
                "message": (
                    f"🛡️ マルウェア解析完了: {sec_report['file_type']} / "
                    f"C2 IP: {', '.join(sec_report['string_analysis']['extracted_ipv4_iocs']) or 'なし'} / "
                    f"DoS脅威: {sec_report['dos_defense']['threat_count']}件 / "
                    f"キーロガー痕跡: {sec_report['keylogger_defense']['indicator_count']}件"
                ),
                "data": {
                    "security_analysis": sec_report,
                    "decisions": [d.__dict__ for d in decisions],
                },
            }

        if resolved_mode == "memo":
            memo_res = self.memo_engine.analyze_japanese_memo(message)
            memo_obj = memo_res["experience_memo"]
            return {
                "response_type": "to_model_studio",
                "active_page": "memo",
                "message": memo_obj["interpreted_summary"],
                "data": {"memo_analysis": memo_res},
            }

        # デフォルト: URL / 動画・造語ソング解析
        url_match = message if message.startswith("http") else "https://www.youtube.com/watch?v=shmup_boss_01"
        if "conlang" in lower or "造語" in message or "曲" in message:
            url_match = "https://example.com/conlang-song-astraea"
        vid_res = self.url_analyzer.analyze_url(url_match)
        return {
            "response_type": "to_model_studio",
            "active_page": "video",
            "message": (
                f"🎬 動画・音声URL解析完了: ジャンル『{vid_res['genre']['primary']}』 "
                f"(信頼度 {vid_res['genre']['confidence_pct']}%) / "
                f"検出話者・声部数: {vid_res['speaker_summary']['total_speakers_count']}人"
            ),
            "data": {"video_analysis": vid_res},
        }


def run_http_server(port: int = 8001) -> None:
    engine = ToModelUnifiedEngine()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw else {}
            res = engine.run(
                message=str(payload.get("message", "")),
                mode=payload.get("mode"),
                action_payload=payload.get("action_payload"),
            )
            body = json.dumps(res, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    print(f"[to_model] Local inference server listening on http://127.0.0.1:{port}")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ToModel CLI & Local Inference Runner")
    parser.add_argument("--url", type=str, help="動画または造語楽曲のURLを解析してJSON出力")
    parser.add_argument("--malware", type=str, help="バイナリ文字列・HEX・DoS・キーロガー検体を解析してJSON出力")
    parser.add_argument("--memo", type=str, help="日本語の体験談（ブラック企業の記録等）を解釈してJSON出力")
    parser.add_argument("--serve", action="store_true", help="ローカルHTTP推論サーバーを起動")
    parser.add_argument("--port", type=int, default=8001, help="HTTPサーバーポート番号 (default: 8001)")
    args = parser.parse_args(argv)

    engine = ToModelUnifiedEngine()
    if args.serve:
        run_http_server(args.port)
        return 0
    if args.url:
        out = engine.run(message=args.url, mode="video")
    elif args.malware:
        out = engine.run(message=args.malware, mode="security")
    elif args.memo:
        out = engine.run(message=args.memo, mode="memo")
    else:
        out = engine.run(message="https://www.youtube.com/watch?v=shmup_boss_01", mode="video")

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
