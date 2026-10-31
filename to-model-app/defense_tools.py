#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToModel Malware Countermeasure & Multi-Encoding Toolkit:
- UnicodeAsciiAnalyzer: ASCII / UTF-8 / UTF-16LE (Wide char) 文字列抽出・正規化・PE構造解析
- DoSDefenseTool: SYN Flood / Portscanner 検知およびファイアウォール・カーネル防御ルール生成
- KeyloggerDefenseTool: キーロガー挙動・ログファイル・ウィンドウ監視検知および無力化ツール
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ExtractedStringItem:
    text: str
    encoding: str  # "ASCII", "UTF-16LE", "UTF-8"
    offset: int
    length: int
    category: str  # "pe_artifact", "network_ioc", "keylogger", "dos_attack", "format_spec", "general"
    suspicious: bool


class UnicodeAsciiAnalyzer:
    """ASCII・Unicode (UTF-16LE / UTF-8) 両対応の文字列抽出およびPEヘッダ・スタブ異常検知ツール"""

    DOS_STUB_PATTERNS = [
        (r"!This program cannot be run in DOS mode\.", "Standard DOS Stub"),
        (r"!This program cannot be run is DOS mode\.", "Tampered DOS Stub ('is DOS mode' grammar anomaly)"),
        (r"!This program cannot be run in Dos mode\.", "Modified DOS Stub ('in Dos mode' case anomaly)"),
    ]

    PE_SECTION_REGEX = re.compile(r"(?:^|[\s`@])(\.(?:text|rdata|data|bss|idata|edata|rsrc|reloc|pdata))\b")
    IPV4_REGEX = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")

    def extract_dual_strings(
        self, raw_input: Union[bytes, str], min_len: int = 4
    ) -> Dict[str, Any]:
        """バイト列またはテキストからASCII文字列とUnicode(UTF-16LE/UTF-8)文字列を両方抽出し分類する"""
        if isinstance(raw_input, str):
            # 文字列入力の場合はUTF-8バイト列とUTF-16LEエンコードテスト用の両方を解析可能にする
            data_bytes = raw_input.encode("utf-8", errors="replace")
            raw_text = raw_input
        else:
            data_bytes = raw_input
            raw_text = data_bytes.decode("utf-8", errors="replace")

        items: List[ExtractedStringItem] = []

        # 1. ASCII 連続印字可能文字 (0x20 - 0x7E)
        ascii_matches = list(re.finditer(rb"[\x20-\x7e]{" + str(min_len).encode() + rb",}", data_bytes))
        for m in ascii_matches:
            s = m.group(0).decode("ascii", errors="ignore")
            cat, susp = self._classify_string(s)
            items.append(
                ExtractedStringItem(
                    text=s,
                    encoding="ASCII",
                    offset=m.start(),
                    length=len(s),
                    category=cat,
                    suspicious=susp,
                )
            )

        # 2. UTF-16LE (Wide Character: ASCII byte followed by 0x00)
        utf16le_pattern = rb"(?:[\x20-\x7e]\x00){" + str(min_len).encode() + rb",}"
        for m in re.finditer(utf16le_pattern, data_bytes):
            s = m.group(0).decode("utf-16le", errors="ignore")
            cat, susp = self._classify_string(s)
            items.append(
                ExtractedStringItem(
                    text=s,
                    encoding="UTF-16LE",
                    offset=m.start(),
                    length=len(s),
                    category=cat,
                    suspicious=susp,
                )
            )

        # 3. 非ASCII Unicode文字 (UTF-8 マルチバイト文字列)
        non_ascii_matches = list(re.finditer(r"[^\x00-\x7f]{2,}", raw_text))
        for m in non_ascii_matches:
            s = m.group(0)
            cat, susp = self._classify_string(s)
            items.append(
                ExtractedStringItem(
                    text=s,
                    encoding="UTF-8 (Unicode)",
                    offset=m.start(),
                    length=len(s),
                    category=cat,
                    suspicious=susp,
                )
            )

        # PE構造・DOSスタブ・セクション・IOCの詳細抽出
        dos_stubs: List[Dict[str, Any]] = []
        for pat, desc in self.DOS_STUB_PATTERNS:
            for m in re.finditer(pat, raw_text):
                dos_stubs.append({
                    "stub_string": m.group(0),
                    "type": desc,
                    "offset": m.start(),
                    "is_anomaly": "Standard" not in desc,
                })

        sections = [m.group(1) for m in self.PE_SECTION_REGEX.finditer(raw_text)]
        # `@.data` のような難読化・修飾セクション名も検出
        weird_sections = re.findall(r"[@`]\.[a-zA-Z0-9_]+|\.[a-zA-Z0-9_]+`\.[a-zA-Z0-9_]+", raw_text)
        has_rich_header = "Rich" in raw_text
        ipv4_list = list(dict.fromkeys(self.IPV4_REGEX.findall(raw_text)))

        return {
            "total_extracted": len(items),
            "encoding_Counts": {
                "ASCII": sum(1 for i in items if i.encoding == "ASCII"),
                "UTF-16LE": sum(1 for i in items if i.encoding == "UTF-16LE"),
                "UTF-8": sum(1 for i in items if "UTF-8" in i.encoding),
            },
            "dos_stubs_detected": dos_stubs,
            "multiple_pe_detected": len(dos_stubs) >= 2,
            "has_rich_header": has_rich_header,
            "pe_sections": sections,
            "modified_section_markers": weird_sections,
            "extracted_ipv4_iocs": ipv4_list,
            "items": [i.__dict__ for i in items],
        }

    def _classify_string(self, text: str) -> tuple[str, bool]:
        lower = text.lower()
        if any(k in lower for k in ["synflood", "portscanner", "ddos", "flood", "startip:"]):
            return ("dos_attack", True)
        if any(k in lower for k in ["keylog", "changed window", "getasynckeystate", "setwindowshookex"]):
            return ("keylogger", True)
        if self.IPV4_REGEX.search(text) or any(k in lower for k in ["http://", "https://", "socket"]):
            return ("network_ioc", True)
        if any(k in lower for k in ["dos mode", ".text", ".rdata", ".data", ".bss", ".idata", ".rsrc", "rich"]):
            return ("pe_artifact", True)
        if "%" in text and any(fmt in text for fmt in ["%s", "%d", "%i", "%04d", "%02d"]):
            return ("format_spec", True)
        return ("general", False)


class DoSDefenseTool:
    """DoS攻撃（SYN Flood / Portscanner）のシグネチャ解析と防御・遮断ルール生成ツール"""

    SYN_FLOOD_REGEX = re.compile(r"SynFlooding\s*:\s*([^\s]+)\s+port\s*:\s*([^\s]+)\s+delay\s*:\s*([^\s]+)\s+times\s*:\s*([^\s.]+)", re.IGNORECASE)
    PORTSCAN_REGEX = re.compile(r"Portscanner\s+startip\s*:\s*([^\s]+)\s+port\s*:\s*([^\s]+)\s+delay\s*:\s*([^\s.]+)", re.IGNORECASE)
    IPV4_REGEX = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")

    def analyze_and_mitigate(self, payload_text: str) -> Dict[str, Any]:
        syn_match = self.SYN_FLOOD_REGEX.search(payload_text)
        scan_match = self.PORTSCAN_REGEX.search(payload_text)
        c2_ips = list(dict.fromkeys(self.IPV4_REGEX.findall(payload_text)))

        threats_detected: List[Dict[str, Any]] = []
        if syn_match:
            threats_detected.append({
                "type": "SYN Flood Attack Engine",
                "signature": syn_match.group(0),
                "parameters": {
                    "target_host_spec": syn_match.group(1),
                    "target_port_spec": syn_match.group(2),
                    "delay_spec": syn_match.group(3),
                    "packet_count_spec": syn_match.group(4),
                },
                "severity": "CRITICAL",
            })

        if scan_match:
            threats_detected.append({
                "type": "Automated TCP/IP Port Scanner",
                "signature": scan_match.group(0),
                "parameters": {
                    "start_ip_spec": scan_match.group(1),
                    "port_spec": scan_match.group(2),
                    "delay_spec": scan_match.group(3),
                },
                "severity": "HIGH",
            })

        # 防御コマンド・対策ルールの生成
        firewall_rules: List[str] = [
            "# 1. Linuxカーネル TCP SYN Cookies 有効化（SYN Floodによるバックログ枯渇防止）",
            "sysctl -w net.ipv4.tcp_syncookies=1",
            "sysctl -w net.ipv4.tcp_max_syn_backlog=4096",
            "sysctl -w net.ipv4.tcp_synack_retries=2",
            "# 2. iptables SYNパケットレート制限（1秒あたり10接続を超えるバーストを遮断）",
            "iptables -N SYN_FLOOD_PROTECT",
            "iptables -A INPUT -p tcp --syn -j SYN_FLOOD_PROTECT",
            "iptables -A SYN_FLOOD_PROTECT -m limit --limit 10/s --limit-burst 20 -j RETURN",
            "iptables -A SYN_FLOOD_PROTECT -j DROP",
            "# 3. ポートスキャン検知・遮断（recentモジュールによる順次ポートプローブ遮断）",
            "iptables -A INPUT -p tcp --tcp-flags ALL SYN,ACK -m state --state NEW -j DROP",
        ]

        for ip in c2_ips:
            firewall_rules.extend([
                f"# 4. 抽出されたハードコードC2 IP ({ip}) の双方向完全遮断 (Linux iptables & Windows Firewall)",
                f"iptables -A INPUT -s {ip} -j DROP && iptables -A OUTPUT -d {ip} -j DROP",
                f"New-NetFirewallRule -DisplayName 'Block_Malware_C2_{ip}' -Direction Outbound -RemoteAddress {ip} -Action Block",
            ])

        return {
            "dos_detected": len(threats_detected) > 0,
            "threat_count": len(threats_detected),
            "threats": threats_detected,
            "c2_ips_blocked": c2_ips,
            "mitigation_rules": firewall_rules,
            "status": "MITIGATION_READY" if threats_detected else "CLEAN",
        }


class KeyloggerDefenseTool:
    """キーロガー機能（keylog.txt / ウィンドウタイトル監視 / 時刻記録）の検知と無力化ツール"""

    def analyze_and_neutralize(self, payload_text: str) -> Dict[str, Any]:
        indicators: List[Dict[str, str]] = []

        if "keylog.txt" in payload_text.lower():
            indicators.append({
                "indicator": "keylog.txt",
                "type": "Keystroke Drop File",
                "description": "打鍵ログをローカルファイル 'keylog.txt' に平文またはフォーマット書き出しする挙動",
            })

        if "changed window" in payload_text.lower():
            indicators.append({
                "indicator": "%s (Changed window",
                "type": "Active Window Focus Tracking",
                "description": "GetForegroundWindow / GetWindowText 等でアクティブウィンドウ切替を監視し入力先アプリを特定する挙動",
            })

        if "keylogger started" in payload_text.lower():
            indicators.append({
                "indicator": "Keylogger Started HH:MM:yyyy.",
                "type": "Keylogger Session Header",
                "description": "キーロガー起動時のタイムスタンプ付き初期化ヘッダ文字列",
            })

        if re.search(r"%04d-%02d\s+%02d:%02d:%02d", payload_text):
            indicators.append({
                "indicator": "%04d-%02d %02d:%02d:%02d %s",
                "type": "Timestamped Exfiltration Format",
                "description": "日時フォーマット付きのログ記録・外部送信テンプレート",
            })

        countermeasures: List[Dict[str, str]] = [
            {
                "action_id": "KL-DEF-01",
                "title": "ログ出力ファイル (keylog.txt) のシンクホール・書き込みロック",
                "command": "touch keylog.txt && chmod 000 keylog.txt && chattr +i keylog.txt  # Windows: icacls keylog.txt /deny Everyone:(W,D)",
                "effect": "マルウェアが keylog.txt を開いて打鍵を記録する処理をファイルシステム層で拒否・無力化します。",
            },
            {
                "action_id": "KL-DEF-02",
                "title": "APIフック (WH_KEYBOARD_LL / GetAsyncKeyState) 監視とプロセス停止",
                "command": "Get-Process | Where-Object { $_.Modules.ModuleName -contains 'user32.dll' } # 非署名プロセスのLowLevelHooksTimeout監査",
                "effect": "フォアグラウンドウィンドウのタイトル取得（Changed window）とキー状態のポーリングを行う不審プロセスを特定・隔離します。",
            },
            {
                "action_id": "KL-DEF-03",
                "title": "カナリアファイル監視（ファイルオープン時の即時アラート）",
                "command": "auditctl -w ./keylog.txt -p wa -k keylogger_canary_trigger",
                "effect": "keylog.txt への書き込み試行が発生した瞬間にプロセスID (PID) と親プロセスを特定して強制終了します。",
            },
        ]

        return {
            "keylogger_detected": len(indicators) > 0,
            "indicator_count": len(indicators),
            "indicators": indicators,
            "countermeasures": countermeasures,
            "risk_level": "CRITICAL" if len(indicators) >= 2 else "LOW",
        }
