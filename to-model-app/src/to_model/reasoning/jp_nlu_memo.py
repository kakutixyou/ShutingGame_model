"""Japanese Context NLU & Structured Memo/Caption JSON Builder (`jp_nlu_memo.py`).

Parses Japanese narratives (such as workplace / black company experiences) and user comments
into quantitative metrics, categories, empathy notes, and structured JSON files.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class ExperienceMemoEntry:
    id: str
    raw_text: str
    categories: List[str]
    monthly_overtime_hours: int
    consecutive_work_days: int
    daily_sleep_hours: float
    severity_score: int
    empathy_response: str
    structured_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JapaneseExperienceAnalyzer:
    """Extracts structured metrics and categories from Japanese workplace narratives."""

    CATEGORY_PATTERNS = {
        "overtime_overload": ["残業", "終電", "徹夜", "みなし残業", "サービス残業"],
        "holiday_deprivation": ["連勤", "休日出勤", "休みなし", "土日出勤"],
        "harassment_pressure": ["怒鳴", "パワハラ", "詰められ", "人格否定", "監視"],
        "sleep_health_risk": ["睡眠", "眠れ", "体調", "めまい", "過労"],
    }

    def analyze(self, text: str, entry_id: str = "exp_001") -> ExperienceMemoEntry:
        categories = [
            cat for cat, words in self.CATEGORY_PATTERNS.items()
            if any(w in text for w in words)
        ] or ["general_workplace_stress"]

        overtime_match = re.search(r"残業[^\d]*(\d{2,3})\s*時間", text)
        overtime_hours = int(overtime_match.group(1)) if overtime_match else (100 if "終電" in text or "徹夜" in text else 40)

        consec_match = re.search(r"(\d{1,3})\s*連勤", text)
        consecutive_days = int(consec_match.group(1)) if consec_match else (14 if "休みなし" in text else 6)

        sleep_match = re.search(r"睡眠[^\d]*(\d+(?:\.\d+)?)\s*時間", text)
        sleep_hours = float(sleep_match.group(1)) if sleep_match else 4.5

        severity = min(100, int(overtime_hours * 0.4 + consecutive_days * 2 + max(0.0, (7.0 - sleep_hours) * 6)))

        empathy = (
            "本当にお疲れ様です。過度な残業や連勤が続く環境で、ここまで耐えてこられたこと自体が大変なことです。"
            "まずはご自身の心身の安全を最優先に記録・整理しておきましょう。"
        )
        summary = (
            f"カテゴリ: {', '.join(categories)} / 推定月間残業: {overtime_hours}h / "
            f"連続勤務: {consecutive_days}日 / 睡眠: {sleep_hours}h (深刻度スコア: {severity}/100)"
        )
        return ExperienceMemoEntry(
            id=entry_id,
            raw_text=text,
            categories=categories,
            monthly_overtime_hours=overtime_hours,
            consecutive_work_days=consecutive_days,
            daily_sleep_hours=sleep_hours,
            severity_score=severity,
            empathy_response=empathy,
            structured_summary=summary,
        )

    def build_memo_and_caption_json(self, text: str, comment_text: str = "") -> Dict[str, Any]:
        entry = self.analyze(text)
        return {
            "experience_memos_json": [entry.to_dict()],
            "comments_json": [{"comment_id": "cmt_001", "text": comment_text or text, "tags": entry.categories}],
            "captions_json": [
                {"start_sec": 0.0, "end_sec": 4.0, "subtitle": entry.structured_summary},
                {"start_sec": 4.0, "end_sec": 9.0, "subtitle": entry.empathy_response},
            ],
        }
