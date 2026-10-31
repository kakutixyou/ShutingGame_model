#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToModel Malware Toolkit: HEX Viewer & Static Binary Inspector (ASCII + Unicode Edition)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple, Union
from to_model.malware.defense_tools import UnicodeAsciiAnalyzer, DoSDefenseTool, KeyloggerDefenseTool


class HexViewer:
    """ASCII・Unicode (UTF-16LE/UTF-8) 両対応のHEXダンプ＆マルウェア総合表層解析ツール"""

    MAGIC_SIGNATURES: List[Tuple[bytes, str]] = [
        (b"MZ", "Windows PE Executable / DLL (MZ header)"),
        (b"!This program", "PE DOS Stub Header Fragment"),
        (b"\x7fELF", "Linux ELF Executable / Shared Object"),
        (b"PK\x03\x04", "ZIP / Office OpenXML Archive"),
    ]

    def __init__(self) -> None:
        self.str_analyzer = UnicodeAsciiAnalyzer()
        self.dos_tool = DoSDefenseTool()
        self.keylog_tool = KeyloggerDefenseTool()

    def format_hex_dump(self, data: Union[bytes, str], max_bytes: int = 320, bytes_per_line: int = 16) -> str:
        raw_bytes = data.encode("utf-8", errors="replace") if isinstance(data, str) else data
        lines: List[str] = []
        truncated = raw_bytes[:max_bytes]

        for offset in range(0, len(truncated), bytes_per_line):
            chunk = truncated[offset : offset + bytes_per_line]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            hex_part = f"{hex_part:<{bytes_per_line * 3}}"
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            lines.append(f"{offset:08x}  {hex_part} |{ascii_part}|")

        if len(raw_bytes) > max_bytes:
            lines.append(f"... (total {len(raw_bytes)} bytes, showing first {max_bytes} bytes)")
        return "\n".join(lines)

    def calculate_entropy(self, data: Union[bytes, str]) -> float:
        raw_bytes = data.encode("utf-8", errors="replace") if isinstance(data, str) else data
        if not raw_bytes:
            return 0.0
        freq: Dict[int, int] = {}
        for b in raw_bytes:
            freq[b] = freq.get(b, 0) + 1
        length = len(raw_bytes)
        return round(-sum((c / length) * math.log2(c / length) for c in freq.values()), 3)

    def inspect_binary_or_strings(self, payload: Union[bytes, str]) -> Dict[str, Any]:
        raw_bytes = payload.encode("utf-8", errors="replace") if isinstance(payload, str) else payload
        raw_text = payload if isinstance(payload, str) else payload.decode("utf-8", errors="replace")

        str_report = self.str_analyzer.extract_dual_strings(payload)
        dos_report = self.dos_tool.analyze_and_mitigate(raw_text)
        keylog_report = self.keylog_tool.analyze_and_neutralize(raw_text)

        file_type = "Multi-Stage PE Dropper (Embedded PE Detected)" if str_report["multiple_pe_detected"] else "PE Binary / Strings Dump"

        return {
            "size_bytes": len(raw_bytes),
            "file_type": file_type,
            "entropy": self.calculate_entropy(raw_bytes),
            "hex_preview": self.format_hex_dump(raw_bytes, max_bytes=320),
            "string_analysis": str_report,
            "dos_defense": dos_report,
            "keylogger_defense": keylog_report,
        }
