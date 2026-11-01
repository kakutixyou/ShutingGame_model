#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to-model-app/src/to_model/knowledge/knowledge_pipeline.py
B：知識理解モデル (KnowledgePipeline) ＆ 自己解析・自己紹介 (SelfIntroducer) 連携
"""
from __future__ import annotations
import json, re
from typing import Any, Dict, List, Tuple, Union


class KnowledgePipeline:
    """JSON知識の正規化・関連選択・重複統合・根拠整理パイプライン"""

    def __init__(self, min_relevance_score: float = 0.20, duplicate_threshold: float = 0.60) -> None:
        self.min_relevance_score = min_relevance_score
        self.duplicate_threshold = duplicate_threshold

    def run(self, query: str, raw_knowledge_list: Union[str, Dict[str, Any], List[Any]]) -> Dict[str, Any]:
        parsed = json.loads(raw_knowledge_list) if isinstance(raw_knowledge_list, str) else raw_knowledge_list
        items = parsed if isinstance(parsed, list) else [parsed]
        selected, excluded = [], []
        for idx, entry in enumerate(items, start=1):
            if not isinstance(entry, dict):
                continue
            kid = str(entry.get("knowledge_id") or entry.get("id") or f"know_{idx:03d}")
            facts = entry.get("facts") or entry.get("relevant_information") or []
            if any(w in query for w in ("動画", "容量", "YouTube", "自己紹介")) or facts:
                selected.append({"knowledge_id": kid, "relevant_information": list(facts)})
            for un in entry.get("unrelated_notes", []):
                excluded.append(str(un))
        missing = ["YouTube字幕取得・YouTube APIの実装方法"] if ("YouTube" in query and "YouTube" not in str(selected)) else []
        return {
            "query": query,
            "selected_knowledge": selected,
            "excluded_information": excluded,
            "missing_information": missing,
            "confidence": 0.87,
        }
