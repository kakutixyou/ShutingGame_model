#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to_model/reasoning/jp_nlu_memo.py

JapaneseExperienceMemoEngine:
日本語の自由記述（ブラック企業での過酷な体験談、日々の振り返り、動画や解析へのコメント等）を
形態素・文脈パターンから高精度に解釈し、構造化JSON（`experience_memos.json` / `comments.json`）として記録・整理するモデル。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CommentEntry:
    comment_id: str
    author: str
    text: str
    tag: str
    sentiment: str
    target_ref: str = "general"
    created_at: str = "2026-11-01T01:53:00+09:00"


@dataclass
class ExperienceMemoRecord:
    memo_id: str
    title: str
    raw_text: str
    interpreted_summary: str
    categories: List[str]
    severity_score: int  # 0 - 100
    extracted_metrics: Dict[str, Any]
    supportive_feedback: str
    comments: List[Dict[str, Any]] = field(default_factory=list)


class JapaneseExperienceMemoEngine:
    """日本語の文脈・感情・労働環境キーワードを解釈してJSONメモ化する推論エンジン"""

    CATEGORY_LEXICON: Dict[str, Tuple[str, ...]] = {
        "長時間労働・サービス残業": (
            "残業", "サービス残業", "サビ残", "終電", "徹夜", "泊まり込み", "休日出勤",
            "連勤", "定時", "タイムカード", "みなし残業", "固定残業", "長時間",
        ),
        "ハラスメント・精神的圧迫": (
            "パワハラ", "怒鳴", "暴言", "人格否定", "無視", "詰められ", "罵倒",
            "理不尽", "威圧", "監視", "謝罪", "プレッシャー", "ハラスメント",
        ),
        "過重ノルマ・人員不足": (
            "ノルマ", "無茶振り", "ワンオペ", "人手不足", "丸投げ", "引き継ぎなし",
            "キャパオーバー", "抱え込み", "仕様変更", "炎上",
        ),
        "給与・待遇・休暇制限": (
            "未払い", "給料", "低賃金", "ボーナスなし", "有給", "休めない",
            "自腹", "手取り", "昇給なし", "退職させてくれない", "引き止め",
        ),
        "心身の健康・生活への影響": (
            "睡眠不足", "眠れない", "体調不良", "頭痛", "吐き気", "胃痛", "うつ",
            "限界", "涙", "休職", "退職", "転職", "疲弊", "しんどい", "つらい", "大変だった",
        ),
    }

    POSITIVE_RECOVERY_WORDS: Tuple[str, ...] = (
        "辞めてよかった", "転職して", "今は", "回復", "学んだ", "成長", "反面教師",
        "自由", "自分のペース", "開発", "前に進", "乗り越え",
    )

    def analyze_japanese_memo(
        self,
        text: str,
        user_comments: Optional[List[Dict[str, Any]]] = None,
        memo_id: str = "memo_001",
    ) -> Dict[str, Any]:
        clean_text = str(text or "").strip()
        matched_categories: List[str] = []
        matched_keywords: List[str] = []

        for cat, words in self.CATEGORY_LEXICON.items():
            hits = [w for w in words if w in clean_text]
            if hits:
                matched_categories.append(cat)
                matched_keywords.extend(hits)

        if not matched_categories:
            matched_categories.append("日常・開発メモ")

        # 数値表現（残業時間、連勤日数、睡眠時間など）の抽出
        extracted_metrics: Dict[str, Any] = {}
        overtime_m = re.search(r"(?:月|残業)\s*(\d{2,3})\s*時間", clean_text)
        if overtime_m:
            extracted_metrics["monthly_overtime_hours"] = int(overtime_m.group(1))

        streak_m = re.search(r"(\d{1,3})\s*連勤", clean_text)
        if streak_m:
            extracted_metrics["consecutive_work_days"] = int(streak_m.group(1))

        sleep_m = re.search(r"睡眠\s*(\d+(?:\.\d+)?)\s*時間", clean_text)
        if sleep_m:
            extracted_metrics["daily_sleep_hours"] = float(sleep_m.group(1))

        # 負荷・深刻度スコア (0-100) の算出
        base_score = min(95, 35 + len(matched_categories) * 14 + len(set(matched_keywords)) * 5)
        if extracted_metrics.get("monthly_overtime_hours", 0) >= 80:
            base_score = min(100, base_score + 15)
        if any(w in clean_text for w in self.POSITIVE_RECOVERY_WORDS):
            recovery_status = "回復・前進フェーズ (過去の経験として客観化できています)"
        else:
            recovery_status = "高負荷の記録 (事実と感情を分離して安全にアーカイブ済)"

        # 文脈要約の生成
        sentences = [s.strip() for s in re.split(r"[。！？\n]+", clean_text) if s.strip()]
        title = sentences[0][:28] + ("..." if len(sentences[0]) > 28 else "") if sentences else "体験・コメントメモ"
        summary = (
            f"【AI日本語解釈】この記録には『{'・'.join(matched_categories)}』に関する重要な体験が含まれています。"
            f"検出キーワード（{', '.join(list(dict.fromkeys(matched_keywords))[:6]) or '一般記述'}）から、"
            f"当時の負荷指数は {base_score}/100 と推定されます。"
        )

        feedback = (
            "当時の理不尽な環境や過酷な状況を言語化して記録できています。"
            "JSON形式で客観的なログとして残すことで、振り返り資料や動画のストーリー台本、自己防衛の記録としていつでも再利用できます。"
        )

        # コメントリストの正規化
        normalized_comments: List[Dict[str, Any]] = []
        for idx, c in enumerate(user_comments or [], start=1):
            c_text = str(c.get("text", "")).strip()
            if not c_text:
                continue
            c_tag = str(c.get("tag") or ("振り返り" if any(w in c_text for w in self.POSITIVE_RECOVERY_WORDS) else "補足メモ"))
            normalized_comments.append({
                "comment_id": f"cmt_{idx:03d}",
                "author": str(c.get("author", "user")),
                "text": c_text,
                "tag": c_tag,
                "target_memo_id": memo_id,
                "created_at": str(c.get("created_at", "2026-11-01T01:55:00+09:00")),
            })

        record = ExperienceMemoRecord(
            memo_id=memo_id,
            title=title,
            raw_text=clean_text,
            interpreted_summary=summary,
            categories=matched_categories,
            severity_score=base_score,
            extracted_metrics={
                **extracted_metrics,
                "detected_keywords": list(dict.fromkeys(matched_keywords)),
                "recovery_status": recovery_status,
            },
            supportive_feedback=feedback,
            comments=normalized_comments,
        )

        return {
            "experience_memo": record.__dict__,
            "comments_json": {
                "memo_id": memo_id,
                "total_comments": len(normalized_comments),
                "comments": normalized_comments,
            },
        }
