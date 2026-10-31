#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToModel Reasoning Engine: TaskPlanner (v0.3 - Unicode/ASCII & DoS/Keylogger Defense Integrated)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


@dataclass
class RequirementSpec:
    raw_prompt: str
    domain: str
    core_goals: List[str]
    extensibility_requirements: List[str]
    tools_to_invoke: List[str]
    tech_stack_hints: List[str]
    knowledge_queries: List[str]


class TaskPlanner:
    """要求理解および対策ツール自動選択プランナー"""

    def parse_user_intent(self, prompt: str) -> RequirementSpec:
        lower = prompt.lower()
        core_goals: List[str] = []
        ext_reqs: List[str] = []
        tools: List[str] = []
        tech_hints: List[str] = []
        queries: List[str] = []

        is_malware = any(
            k in lower or k in prompt
            for k in [
                "dos mode", "keylog", "synflood", "portscanner", "マルウェア",
                "キーロガー", "dos攻撃", "unicode", "ascii", ".text", ".rdata",
            ]
        )

        if is_malware:
            domain = "malware_defense"
            core_goals.append("バイナリ/文字列からの脅威抽出（ASCII・UTF-16LE・UTF-8対応）")
            tools.append("UnicodeAsciiAnalyzer")
            queries.append("dual_encoding_pe_inspection")

            if any(k in lower or k in prompt for k in ["dos", "synflood", "portscanner"]):
                core_goals.append("DoS攻撃（SYN Flooding / Portscanner）の検知と遮断ルール生成")
                tools.append("DoSDefenseTool")
                queries.append("dos_synflood_mitigation")

            if any(k in lower or k in prompt for k in ["keylog", "キーロガー", "changed window"]):
                core_goals.append("キーロガー（keylog.txt / ウィンドウ監視）の検知と無力化対策")
                tools.append("KeyloggerDefenseTool")
                queries.append("keylogger_sinkhole_defense")

            ext_reqs.extend([
                "複数PEヘッダ（埋め込みPE・改조DOSスタブ）検知",
                "ハードコードC2 IPアドレスの自動ファイアウォール遮断",
            ])
        else:
            domain = "video_app"
            core_goals.append("動画メタデータ・字幕タイムライン整理")
            tools.append("YouTubeTranscriptPlugin")
            tech_hints.extend(["Python (FastAPI)", "React 18"])
            queries.append("youtube_transcript_plugin_architecture")

        return RequirementSpec(
            raw_prompt=prompt,
            domain=domain,
            core_goals=core_goals,
            extensibility_requirements=ext_reqs,
            tools_to_invoke=tools,
            tech_stack_hints=tech_hints,
            knowledge_queries=queries,
        )
