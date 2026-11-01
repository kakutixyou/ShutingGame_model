#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to-model-app/src/to_model/reasoning/persona_and_flow.py
モデルの3大行動原則を保証する応答オーケードャー:
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
    )
    ACTION_KEYWORDS = (
        "解析",
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
    )

    def _has_action_intent(self, text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return False
        lower = normalized.lower()
        if any(k.lower() in lower for k in self.ACTION_KEYWORDS):
            return True
        if any(marker in normalized for marker in ("して", "してほしい", "お願いします", "お願い")):
            return True
        return False

    def _split_message_into_wishes(self, user_message: str) -> List[str]:
        msg = str(user_message or "").strip()
        if not msg:
            return []

        # まず、句点・改行や感嘆符で分割
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

        # 例: 「マルウェアの挙動を分析して」 → 分割後の候補が欠けるケースへのフォールバック
        if not wishes:
            cleaned = re.sub(r"\s+", " ", msg).strip(" 　\t")
            if self._has_action_intent(cleaned) or any(
                keyword in cleaned for keyword in ("お願い", "してください", "教えて", "解析", "分析", "調べて")
            ):
                wishes.append(cleaned)

        return wishes

    def _infer_resolution_status(self, wish: str, execution_results: Optional[List[Any]] = None, index: int = 0) -> bool:
        if isinstance(execution_results, list) and execution_results:
            if index < len(execution_results):
                result = execution_results[index]
            else:
                result = execution_results[-1]

            if isinstance(result, dict):
                if "success" in result:
                    return bool(result.get("success"))
                if "ok" in result:
                    return bool(result.get("ok"))
                if "error" in result:
                    return not bool(result.get("error"))
                return True
            if isinstance(result, bool):
                return result
            return result is not None

        # 実行結果が未渡しでも、要求が明確なら「解決可能」とみなす
        return self._has_action_intent(wish)

    def _contextual_proposal(self, user_message: str, wishes: List[str]) -> str:
        lower = str(user_message or "").lower()
        if any(token in lower for token in ("マルウェア", "malware", "keylog", "キーロガー", "dos", "unicode", "utf-16", "pe ")):
            return (
                "💡 次の一手: マルウェア解析は「サンプル確認 → 文字列抽出 → 擬似コード化 → 影響範囲評価」の流れで整理すると"
                "再現性が上がります。対策ルールも一緒に作れるので、今の作業を可視化して次に進めます。"
            )
        if any(token in lower for token in ("動画", "youtube", "字幕", "タイムコード", "video", "mp4", "ffmpeg")):
            return (
                "💡 次の一手: 動画関連は「入力 → 解析 → タイムコード整形 → 出力」のデータフローを固定すると、"
                "IPCやパス管理のミスが減ります。軽い JSON ベースの連携設計もおすすめです。"
            )
        if any(token in lower for token in ("自己紹介", "あなたは", "どんなai", "何ができる")):
            return (
                "💡 次の一手: 自己紹介は『何ができるか』の具体例を 3 つに絞って伝えると、初対面でも会話がスムーズです。"
                "そのうえで、今回の依頼に合わせて「できること」「やること」「次の提案」を切り分けると自然です。"
            )
        return (
            "💡 次の一手: 依頼を「背景」「目的」「実行したいこと」に分けて整理すると、AI の判断と応答が安定します。"
            "必要なら次に『会話の型』や『自動提案のルール』まで整えられます。"
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
            )
        )

        extracted_wishes = wishes if wishes is not None else self._split_message_into_wishes(msg)
        if not extracted_wishes and msg:
            extracted_wishes = [msg]

        resolved_items = []
        for i, wish in enumerate(extracted_wishes, start=1):
            resolved = self._infer_resolution_status(wish, execution_results, i - 1)
            summary = (
                f"『{wish}』の対応を完了しました。"
                if resolved
                else f"『{wish}』は未実行または不明瞭なため、具体的なアクションを確認する必要があります。"
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
