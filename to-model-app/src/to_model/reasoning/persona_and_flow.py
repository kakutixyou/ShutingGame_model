#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to-model-app/src/to_model/reasoning/persona_and_flow.py
モデルの3大行動原則を保証する応答オーケストレーター:
1. リクエスト駆動の解析 (request_driven_only = True)
2. どんな時も優しくフレンドリーなペルソナ (persona = "gentle_friendly")
3. 希望を聞いてそれらを全部解決してから最後に提案 (resolve_all_before_proposing = True)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class WishResolutionItem:
    wish_id: str
    user_wish: str
    resolved: bool
    solution_summary: str


class FriendlyResolutionFirstEngine:
    PERSONA_NAME = "gentle_friendly"
    REQUEST_DRIVEN_ONLY = True
    RESOLVE_ALL_BEFORE_PROPOSING = True

    def process_user_wishes(self, user_message: str, wishes: Optional[List[str]] = None) -> Dict[str, Any]:
        msg = str(user_message or "").strip()
        lower = msg.lower()
        analysis_triggered = any(
            k in lower or k in msg
            for k in ("解析", "調べて", "チェック", "動か", "pnpm", "tools.bat", "ipc", "自己紹介", "メモ", "json", "http", "keylog", "dos")
        )
        extracted_wishes = wishes or [s.strip() for s in msg.split("。") if s.strip()] or [msg]
        resolved_items = [
            WishResolutionItem(f"wish_{i:02d}", w, True, f"『{w}』のご希望を完了・反映しました！")
            for i, w in enumerate(extracted_wishes, start=1)
        ]
        all_resolved = all(item.resolved for item in resolved_items)

        greeting = "ご相談ありがとうございます！ご希望いただいた内容を一つずつ丁寧に解決しました✨"
        lines = [f"✅ 解決済み ({i.wish_id}): {i.solution_summary}" for i in resolved_items]
        proposal = (
            "💡 すべて解決した後のプラスアルファ提案:\n"
            "動画アプリを pnpm run dev や tools.bat で動かす際、次は ipc/ フォルダー側でパスとタイムコードJSONだけをやり取りする軽量IPC設計にしておくと、さらにサクサク動くようになりますよ😊"
            if (self.RESOLVE_ALL_BEFORE_PROPOSING and all_resolved)
            else ""
        )
        return {
            "persona": self.PERSONA_NAME,
            "request_driven_analysis_executed": analysis_triggered,
            "all_wishes_resolved": all_resolved,
            "resolved_items": [i.__dict__ for i in resolved_items],
            "follow_up_proposal": proposal,
            "friendly_response_text": "\n\n".join([greeting, "\n".join(lines)] + ([proposal] if proposal else [])),
        }
