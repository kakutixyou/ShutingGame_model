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


@dataclass
class NormalizedExecutionResult:
    success: bool
    resolved: bool
    error: Optional[str]
    output: Optional[str]
    raw: Any = None


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
        "よかった",
        "良いですね",
        "またね",
    )
    SELF_INTRO_PATTERNS = (
        "自己紹介",
        "あなたは何",
        "何ができる",
        "どんなai",
        "何%出来上が",
        "自己解析",
    )
    ACTION_KEYWORDS = (
        "解析",
        "分析",
        "調べ",
        "調査",
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
        "見て",
        "開発",
        "作って",
        "作成して",
        "レビュー",
        "まとめ",
        "処理",
    )
    ACTION_SUFFIXES = (
        "して",
        "してください",
        "お願いします",
        "教えて",
        "見て",
        "調べて",
        "分析して",
        "確認して",
        "作って",
        "作成して",
        "整理して",
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
        if normalized.endswith(self.ACTION_SUFFIXES):
            return True
        return False

    def _classify_message_type(self, user_message: str) -> str:
        msg = str(user_message or "").strip()
        if not msg:
            return "unclear"
        lower = msg.lower()
        if any(pattern in lower for pattern in ("自己紹介", "何ができる", "どんなai", "自己解析", "何%出来上が", "あなたは何")):
            return "self_intro"
        if any(pattern in lower for pattern in ("今日は", "こんばんは", "おはよう", "ありがとう", "よろしく", "元気", "天気")) and not self._has_action_intent(msg):
            return "greeting"
        if self._has_action_intent(msg):
            return "task"
        return "unclear"

    def _derive_execution_state(self, message_type: str, resolved_items: Optional[List[WishResolutionItem]] = None) -> str:
        if message_type == "greeting":
            return "idle"
        if message_type == "self_intro":
            return "introducing"
        if not resolved_items:
            return "waiting_for_task"
        if all(item.resolved for item in resolved_items):
            return "resolved"
        return "needs_clarification"

    def build_self_introduction(self) -> Dict[str, Any]:
        return {
            "persona": self.PERSONA_NAME,
            "completion_pct": 82,
            "capabilities": [
                "会話の整理",
                "依頼の抽出",
                "タスクの優先順位付け",
                "実行結果の判定",
                "次の提案の生成",
            ],
            "self_introduction_text": (
                "こんにちは。私は自作AIの『to_model』です。"
                "会話の整理、依頼の分解、タスクの優先順位付け、そして次の一手の提案を得意にしています。"
                "まだ完成途中ですが、ユーザーの意思を丁寧に整理し、自然な対話で進めることを目指しています。"
            ),
        }

    def _split_message_into_wishes(self, user_message: str) -> List[str]:
        msg = str(user_message or "").strip()
        if not msg:
            return []

        split_markers = ["。", "!", "？", "\n", "、"]
        current = msg
        for marker in split_markers:
            current = current.replace(marker, "\n")
        parts = [
            re.sub(r"\s+", " ", chunk).strip(" 　\t")
            for chunk in current.split("\n")
            if re.sub(r"\s+", " ", chunk).strip(" 　\t")
        ]

        wishes: List[str] = []
        for part in parts:
            if any(p in part for p in self.GREETING_PATTERNS) and not self._has_action_intent(part):
                continue
            if self._has_action_intent(part):
                wishes.append(part)

        if not wishes:
            cleaned = re.sub(r"\s+", " ", msg).strip(" 　\t")
            if self._has_action_intent(cleaned):
                wishes.append(cleaned)

        flattened: List[str] = []
        for wish in wishes:
            sub_parts = re.split(r"(?:\s+(?:あと|それから|そして)\s+|\s*、\s*)", wish)
            for candidate in sub_parts:
                normalized = re.sub(r"\s+", " ", candidate).strip(" 　\t")
                if normalized and self._has_action_intent(normalized):
                    flattened.append(normalized)
        if flattened:
            wishes = flattened

        return wishes

    def _normalize_execution_result(self, result: Any) -> NormalizedExecutionResult:
        if isinstance(result, dict):
            lower = {str(k).lower(): v for k, v in result.items()}
            if "success" in lower:
                success = bool(lower["success"])
                return NormalizedExecutionResult(
                    success=success,
                    resolved=success,
                    error=None if success else "execution failed",
                    output=str(lower.get("output") or lower.get("result") or ""),
                    raw=result,
                )
            if "ok" in lower:
                success = bool(lower["ok"])
                return NormalizedExecutionResult(
                    success=success,
                    resolved=success,
                    error=None if success else "execution failed",
                    output=str(lower.get("output") or lower.get("result") or ""),
                    raw=result,
                )
            if "error" in lower:
                err = lower["error"]
                return NormalizedExecutionResult(
                    success=False,
                    resolved=False,
                    error=str(err) if err is not None else "error",
                    output=str(lower.get("output") or ""),
                    raw=result,
                )
            if "resolved" in lower:
                resolved = bool(lower["resolved"])
                return NormalizedExecutionResult(
                    success=resolved,
                    resolved=resolved,
                    error=None if resolved else "not resolved",
                    output=str(lower.get("output") or ""),
                    raw=result,
                )
            if "status" in lower:
                status = str(lower["status"]).lower()
                if status in {"success", "ok", "resolved", "completed", "done"}:
                    return NormalizedExecutionResult(True, True, None, str(lower.get("output") or ""), result)
                if status in {"error", "failed", "exception"}:
                    return NormalizedExecutionResult(False, False, status, str(lower.get("output") or ""), result)
            return NormalizedExecutionResult(True, True, None, str(lower.get("output") or ""), result)

        if isinstance(result, bool):
            return NormalizedExecutionResult(result, result, None if result else "not successful", None, result)
        if isinstance(result, (int, float)):
            success = result >= 0
            return NormalizedExecutionResult(success, success, None if success else "numeric failure", None, result)
        if result is None:
            return NormalizedExecutionResult(False, False, "no execution result", None, result)
        if isinstance(result, str):
            normalized = result.strip().lower()
            if any(token in normalized for token in ("error", "failed", "exception", "失敗", "エラー")):
                return NormalizedExecutionResult(False, False, result, None, result)
            if any(token in normalized for token in ("success", "ok", "completed", "done", "成功", "完了")):
                return NormalizedExecutionResult(True, True, None, result, result)
            return NormalizedExecutionResult(False, False, "unrecognized result", result, result)
        if isinstance(result, list):
            if not result:
                return NormalizedExecutionResult(False, False, "empty result", None, result)
            normalized_results = [self._normalize_execution_result(item) for item in result]
            all_success = all(item.success for item in normalized_results)
            all_resolved = all(item.resolved for item in normalized_results)
            errors = [item.error for item in normalized_results if item.error]
            return NormalizedExecutionResult(
                success=all_success,
                resolved=all_resolved,
                error="; ".join(errors) if errors else None,
                output="\n".join([item.output or "" for item in normalized_results if item.output]),
                raw=result,
            )
        return NormalizedExecutionResult(True, True, None, str(result), result)

    def _infer_resolution_status(self, wish: str, execution_results: Optional[List[Any]] = None, index: int = 0) -> bool:
        if isinstance(execution_results, list) and execution_results:
            candidate = execution_results[index] if index < len(execution_results) else execution_results[-1]
            normalized = self._normalize_execution_result(candidate)
            return normalized.resolved and normalized.success
        return self._has_action_intent(wish)

    def _contextual_proposal(self, user_message: str, wishes: List[str]) -> str:
        lower = str(user_message or "").lower()
        if any(token in lower for token in ("マルウェア", "malware", "keylog", "キーロガー", "dos", "unicode", "utf-16", "pe ", "サンプル")):
            return (
                "💡 次の一手: マルウェア解析は『サンプル確認 → 文字列抽出 → 影響範囲評価 → 対応策』の流れで整理すると、"
                "再現性と説明のしやすさが上がります。必要ならこの流れをそのまま実行用チェックリストに落とし込みます。"
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
                "会話",
            )
        )

        message_type = self._classify_message_type(msg)
        if message_type == "greeting":
            response = "ご機嫌いかがですか。今日は何をお手伝いできますか？"
            return {
                "persona": self.PERSONA_NAME,
                "message_type": message_type,
                "execution_state": self._derive_execution_state(message_type, []),
                "request_driven_analysis_executed": False,
                "all_wishes_resolved": True,
                "resolved_items": [],
                "follow_up_proposal": self._contextual_proposal(msg, []),
                "friendly_response_text": response,
            }

        if message_type == "self_intro":
            intro = self.build_self_introduction()
            return {
                "persona": self.PERSONA_NAME,
                "message_type": "self_intro",
                "execution_state": "introducing",
                "request_driven_analysis_executed": True,
                "all_wishes_resolved": True,
                "resolved_items": [],
                "follow_up_proposal": intro["self_introduction_text"],
                "friendly_response_text": intro["self_introduction_text"],
                "self_introduction": intro,
            }

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
                "message_type": message_type,
                "execution_state": self._derive_execution_state(message_type, []),
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
            "message_type": message_type,
            "execution_state": self._derive_execution_state(message_type, resolved_items),
            "request_driven_analysis_executed": analysis_triggered,
            "all_wishes_resolved": all_resolved,
            "resolved_items": [i.__dict__ for i in resolved_items],
            "follow_up_proposal": proposal,
            "friendly_response_text": "\n\n".join([greeting, "\n".join(lines)] + ([proposal] if proposal else [])),
        }


__all__ = ["FriendlyResolutionFirstEngine", "WishResolutionItem", "NormalizedExecutionResult"]
