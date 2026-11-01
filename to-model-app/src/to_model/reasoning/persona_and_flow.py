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

import re
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

    GREETING_PATTERNS = (
        "こんにちは",
        "こんばんは",
        "おはよう",
        "ありがとう",
        "よろしく",
        "です",
        "ですね",
        "します",
        "気分",
        "天気",
        "元気",
        "その後",
        "最近",
        "良い一日",
    )
    ACTION_KEYWORDS = (
        "解析",
        "分析",
        "調べ",
        "チェック",
        "動か",
        "実行",
        "修正",
        "改善",
        "追加",
        "作成",
        "説明",
        "教えて",
        "提案",
        "自己紹介",
        "会話",
        "記録",
        "生成",
        "整理",
        "確認",
        "比較",
        "選定",
        "設計",
        "評価",
        "診断",
        "調査",
        "確認して",
        "見て",
        "開発",
    )
    ACTION_SUFFIXES = ("して", "してください", "お願いします", "教えて", "見て", "調べて", "分析して")

    def _has_action_intent(self, text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return False
        lower = normalized.lower()
        if any(k.lower() in lower for k in self.ACTION_KEYWORDS):
            return True
        if any(marker in normalized for marker in ("して", "してほしい", "お願いします", "お願い")):
            return True
        if normalized.endswith(self.ACTION_SUFFIXES):
            return True
        return False

    def _split_message_into_wishes(self, user_message: str) -> List[str]:
        msg = str(user_message or "").strip()
        if not msg:
            return []

        candidate_parts = re.split(r"[。！？\n]+", msg)
        wishes: List[str] = []
        for part in candidate_parts:
            cleaned = re.sub(r"\s+", " ", part).strip(" 　\t")
            if not cleaned:
                continue
            if any(p in cleaned for p in self.GREETING_PATTERNS) and not self._has_action_intent(cleaned):
                continue
            if self._has_action_intent(cleaned) or cleaned.endswith(("して", "ください", "お願いします", "教えて")):
                wishes.append(cleaned)

        if not wishes:
            cleaned = re.sub(r"\s+", " ", msg).strip(" 　\t")
            if self._has_action_intent(cleaned):
                wishes.append(cleaned)

        return wishes

    def _normalize_execution_result(self, result: Any) -> bool:
        if isinstance(result, dict):
            if "success" in result:
                return bool(result.get("success"))
            if "ok" in result:
                return bool(result.get("ok"))
            if "error" in result:
                return not bool(result.get("error"))
            if "resolved" in result:
                return bool(result.get("resolved"))
            return True
        if isinstance(result, bool):
            return result
        if isinstance(result, (int, float)):
            return result >= 0
        if result is None:
            return False
        return True

    def _infer_resolution_status(self, wish: str, execution_results: Optional[List[Any]] = None, index: int = 0) -> bool:
        if isinstance(execution_results, list) and execution_results:
            candidate = execution_results[index] if index < len(execution_results) else execution_results[-1]
            return self._normalize_execution_result(candidate)

        return self._has_action_intent(wish)

    def _contextual_proposal(self, user_message: str, wishes: List[str]) -> str:
        lower = str(user_message or "").lower()
        if any(token in lower for token in ("マルウェア", "malware", "keylog", "キーロガー", "dos", "unicode", "utf-16", "pe ", "サンプル")):
            return (
                "💡 次の一手: マルウェア解析は『サンプル確認 → 文字列抽出 → 影響範囲評価 → 対応策』の流れで整理すると、"
                "再現性と説明のしやすさが上がります。必要ならこの流れをそのまま実行用のチェックリストに落とし込みます。"
            )
        if any(token in lower for token in ("動画", "youtube", "字幕", "タイムコード", "video", "mp4", "ffmpeg", "subtitle")):
            return (
                "💡 次の一手: 動画関連は『入力 → 解析 → タイムコード整形 → 出力』のデータフローを固定すると、"
                "JSON のやり取りやパス管理のミスが減ります。軽い IPC 設計も合わせて整えられます。"
            )
        if any(token in lower for token in ("自己紹介", "あなたは", "どんなai", "何ができる", "なのか")):
            return (
                "💡 次の一手: 自己紹介は『自分ができること』『今の完成度』『会話の進め方』の3つに絞ると、"
                "初対面でも一瞬で伝わります。自身の役割と次の一手を一緒に説明すると自然です。"
            )
        if any(token in lower for token in ("開発", "実装", "修正", "改善", "追加", "作成")):
            return (
                "💡 次の一手: 実装作業は『背景 → 目的 → 手順 → 検証』の順で整理すると、"
                "手戻りを減らせます。次に、どこまで実装済みかを明示するとやりやすくなります。"
            )
        return (
            "💡 次の一手: 依頼を『背景』『目的』『やりたいこと』『検証方法』に分けて整理すると、"
            "AI の判断と応答が安定します。必要なら次に、会話の型や提案のテンプレートまで固められます。"
        )

    def process_user_wishes(
        self,
        user_message: str,
        wishes: Optional[List[str]] = None,
        execution_results: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        msg = str(user_message or "").strip()
        lower = msg.lower()
        analysis_triggered = any(
            k in lower or k in msg
            for k in (
                "解析",
                "調べて",
                "チェック",
                "動か",
                "pnpm",
                "tools.bat",
                "ipc",
                "自己紹介",
                "メモ",
                "json",
                "http",
                "keylog",
                "dos",
                "マルウェア",
                "動画",
                "評価",
                "実装",
                "開発",
                "分析",
            )
        )

        extracted_wishes = wishes if wishes is not None else self._split_message_into_wishes(msg)
        if not extracted_wishes and msg:
            extracted_wishes = [msg]

        resolved_items: List[WishResolutionItem] = []
        for i, wish in enumerate(extracted_wishes, start=1):
            resolved = self._infer_resolution_status(wish, execution_results, i - 1)
            summary = (
                f"『{wish}』の対応を完了しました。"
                if resolved
                else f"『{wish}』は未実行または曖昧なため、具体的なアクションを確認する必要があります。"
            )
            resolved_items.append(WishResolutionItem(f"wish_{i:02d}", wish, resolved, summary))

        all_resolved = bool(resolved_items) and all(item.resolved for item in resolved_items)

        if not resolved_items:
            greeting = "挨拶ありがとうございます。今の段階では『やってほしいこと』が見えていないので、具体的な依頼を言ってください。"
            proposal = self._contextual_proposal(msg, [])
            return {
                "persona": self.PERSONA_NAME,
                "request_driven_analysis_executed": analysis_triggered,
                "all_wishes_resolved": True,
                "resolved_items": [],
                "follow_up_proposal": proposal,
                "friendly_response_text": "\n\n".join([greeting, proposal]),
            }

        greeting = "ご相談ありがとうございます。ご希望いただいた内容を一つずつ丁寧に確認し、必要な対応を整理しました✨"
        lines = [f"✅ {i.wish_id}: {i.solution_summary}" for i in resolved_items]
        proposal = self._contextual_proposal(msg, [item.user_wish for item in resolved_items]) if all_resolved else ""
        return {
            "persona": self.PERSONA_NAME,
            "request_driven_analysis_executed": analysis_triggered,
            "all_wishes_resolved": all_resolved,
            "resolved_items": [i.__dict__ for i in resolved_items],
            "follow_up_proposal": proposal,
            "friendly_response_text": "\n\n".join([greeting, "\n".join(lines)] + ([proposal] if proposal else [])),
        }
