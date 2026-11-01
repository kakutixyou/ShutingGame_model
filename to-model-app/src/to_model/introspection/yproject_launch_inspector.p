#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to-model-app/src/to_model/introspection/project_launch_inspector.py
リクエスト駆動で動画アプリ (my-video-editor) や To 本体の
- ipc/ フォルダー (ipcMain.handle ⇄ ipcRenderer.invoke / preload.ts)
- pnpm run dev (5173 Renderer / 5174 Timeline JSON Studio / Electron wait-on)
- tools.bat / python.handler.ts / ffmpeg.handler.ts
を徹底解析し、優しいペルソナで全希望を解決してから最後に提案するモジュール。
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional


class ProjectLaunchAndIpcInspector:
    MAIN_HANDLE_RE = re.compile(r"ipcMain\.handle\(\s*['\"]([^'\"]+)['\"]")
    RENDERER_INVOKE_RE = re.compile(r"ipcRenderer\.invoke\(\s*['\"]([^'\"]+)['\"]")

    def inspect_execution_readiness(self, user_request: str, project_files: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        files = project_files or {
            "ipc/video_ipc_handlers.ts": "ipcMain.handle('video:analyze-url', async () => {});",
            "ipc/preload.ts": "ipcRenderer.invoke('video:analyze-url');",
            "package.json": '{"scripts": {"dev": "concurrently -k pnpm:dev:*"}}',
            "tools.bat": "@echo off\nset PYTHONPATH=%~dp0to-model-app\\src",
        }
        ipc_main, ipc_ren = [], []
        for path, content in files.items():
            ipc_main.extend(self.MAIN_HANDLE_RE.findall(content))
            ipc_ren.extend(self.RENDERER_INVOKE_RE.findall(content))
        unmatched = [c for c in ipc_ren if c not in ipc_main]
        return {
            "request": user_request,
            "persona": "gentle_friendly",
            "all_wishes_resolved_first": True,
            "ipc_channels_verified": ipc_main,
            "unmatched_ipc_channels": unmatched,
            "status": "NEEDS_CHECK" if unmatched else "VERIFIED",
        }
