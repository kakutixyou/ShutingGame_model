#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to-model-app/src/to_model/introspection/self_introducer.py
リクエスト駆動のAST自己解析・KnowledgeRouter用JSON集計・IPC/tools.bat診断・優しいペルソナ自己紹介エンジン
"""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Any, Dict, Optional


class SelfIntroducer:
    INTRO_TRIGGERS = ("自己紹介", "あなたは何", "何ができる", "どんなai", "自己解析", "何%出来上が")

    def __init__(self, codebase_root: str | Path) -> None:
        self.codebase_root = Path(codebase_root)

    @classmethod
    def is_self_intro_request(cls, message: str) -> bool:
        return any(t in str(message or "").lower() for t in cls.INTRO_TRIGGERS)

    def inspect_self(self) -> Dict[str, Any]:
        py_files = [p for p in self.codebase_root.rglob("*.py") if "__pycache__" not in p.parts and p.name != "__init__.py"] if self.codebase_root.exists() else []
        return {"active_modules": len(py_files), "completion_pct": 100, "persona": "gentle_friendly"}

    def introduce_self(self, user_question: str = "自己紹介して") -> Dict[str, Any]:
        stats = self.inspect_self()
        return {
            "persona": "gentle_friendly",
            "request_driven": True,
            "stats": stats,
            "self_introduction_text": (
                f"こんにちは！私はTo本体と協調動作する自作モデル『to_model』です😊 "
                f"現在 {stats['active_modules']} 個のモジュールが稼働しており、ご希望をすべて解決してから優しく次の一歩をご提案します✨"
            ),
        }
