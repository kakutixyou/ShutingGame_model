#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToModel Reasoning Engine: DecisionPolicy (v0.3 - Malware Countermeasure Routing)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class DecisionRule:
    rule_id: str
    topic: str
    decision: str
    rationale: str


class DecisionPolicy:
    """マルウェア解析・防御ツール選択および動画編集アーキテクチャの意思決定エンジン"""

    def select_defense_policy(self, analysis_report: Dict[str, Any]) -> List[DecisionRule]:
        rules: List[DecisionRule] = []
        str_info = analysis_report.get("string_analysis", {})
        dos_info = analysis_report.get("dos_defense", {})
        kl_info = analysis_report.get("keylogger_defense", {})

        if str_info.get("multiple_pe_detected"):
            rules.append(
                DecisionRule(
                    rule_id="DEF-PE-01",
                    topic="複数PEヘッダ（埋め込みドロッパー構造）検知",
                    decision="メモリダンプ隔離 ＆ セクション境界（.text/.bss/.rsrc）の静的切り出し",
                    rationale=(
                        "外殻PE ('!This program cannot be run is DOS mode.') の内部オフセット 118 に"
                        "第2のPE ('!This program cannot be run in Dos mode.') が埋め込まれているため、"
                        "実行せずに内部ペイロードを分離解析する。"
                    ),
                )
            )

        if dos_info.get("dos_detected"):
            c2_ips = ", ".join(dos_info.get("c2_ips_blocked", [])) or "N/A"
            rules.append(
                DecisionRule(
                    rule_id="DEF-DOS-01",
                    topic="DoS攻撃 (SynFlooding / Portscanner) 対策",
                    decision=f"TCP SYN Cookies有効化 ＋ SYNレート制限 ＋ C2 IP ({c2_ips}) 即時DROP",
                    rationale=(
                        "`SynFlooding:%s port: %i delay:%i times:%i` および `Portscanner startip:%s` "
                        "のフォーマット文字列が検出されたため、ネットワーク層でSYNフラッドとスキャンを遮断する。"
                    ),
                )
            )

        if kl_info.get("keylogger_detected"):
            rules.append(
                DecisionRule(
                    rule_id="DEF-KL-01",
                    topic="キーロガー (keylog.txt / Changed window) 対策",
                    decision="keylog.txt のイミュータブル（書き込み禁止）ロック ＋ カナリア監査 ＋ フックAPI遮断",
                    rationale=(
                        "`keylog.txt` への記録と `%s (Changed window` によるアクティブウィンドウ監視が"
                        "確認されたため、ログファイルのシンクホール化とフック解除を優先適用する。"
                    ),
                )
            )

        return rules
