#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scaffold_to_model_app.py
"""
`to-model-app/` の推奨フォルダー・初期ファイル一式を自動生成するスキャフォールドスクリプト。
ユーザー設計のツリーをベースに、以下の実戦向け拡張を含めて構築する:
  1. knowledge/          : 薬名・病名等を .py/.go から分離する JSON 辞書置き場
  2. datasets/feedback/  : 実運用で「あれ？」と言われた発話や低確信度ログの自動収集先
  3. src/to_model/grammar/ : 8モジュール文法解析・指示語照応（さっき・あれ・あのあれ）
  4. adapters/hybrid_adapter.py : 自作モデル・Ollama・ルール応答をシームレスに切り替えるアダプター
"""
from __future__ import annotations

import json
from pathlib import Path

DIRECTORIES = [
    "configs",
    "knowledge/medical",
    "knowledge/grammar",
    "src/to_model/api",
    "src/to_model/adapters",
    "src/to_model/llm",
    "src/to_model/tokenizer",
    "src/to_model/grammar",
    "src/to_model/intent",
    "src/to_model/reasoning",
    "src/to_model/training",
    "src/to_model/inference",
    "src/to_model/evaluation",
    "src/to_model/safety",
    "src/to_model/common",
    "datasets/raw",
    "datasets/processed",
    "datasets/training",
    "datasets/validation",
    "datasets/test",
    "datasets/feedback",
    "artifacts/checkpoints",
    "artifacts/tokenizer",
    "artifacts/intent_models",
    "artifacts/evaluation_reports",
    "scripts",
    "tests",
]

FILES = [
    "README.md",
    "pyproject.toml",
    ".gitignore",
    "configs/model_config.json",
    "configs/training_config.json",
    "configs/inference_config.json",
    "configs/evaluation_config.json",
    "knowledge/medical/medical_conditions.json",
    "knowledge/grammar/deictics.json",
    "knowledge/grammar/modality.json",
    "knowledge/grammar/orthography.json",
    "src/to_model/__init__.py",
    "src/to_model/main.py",
    "src/to_model/api/__init__.py",
    "src/to_model/api/app.py",
    "src/to_model/api/routes.py",
    "src/to_model/api/schemas.py",
    "src/to_model/api/error_handlers.py",
    "src/to_model/adapters/__init__.py",
    "src/to_model/adapters/base_adapter.py",
    "src/to_model/adapters/ollama_adapter.py",
    "src/to_model/adapters/local_model_adapter.py",
    "src/to_model/adapters/hybrid_adapter.py",
    "src/to_model/llm/__init__.py",
    "src/to_model/llm/config.py",
    "src/to_model/llm/model.py",
    "src/to_model/llm/transformer.py",
    "src/to_model/llm/attention.py",
    "src/to_model/llm/embeddings.py",
    "src/to_model/llm/positional_encoding.py",
    "src/to_model/llm/generation.py",
    "src/to_model/llm/lora_adapter.py",
    "src/to_model/tokenizer/__init__.py",
    "src/to_model/tokenizer/tokenizer.py",
    "src/to_model/tokenizer/vocabulary.py",
    "src/to_model/tokenizer/normalization.py",
    "src/to_model/grammar/__init__.py",
    "src/to_model/grammar/grammar_engine.py",
    "src/to_model/grammar/reference_resolver.py",
    "src/to_model/grammar/ambiguity_detector.py",
    "src/to_model/intent/__init__.py",
    "src/to_model/intent/custom_intent_model.py",
    "src/to_model/intent/feature_extractor.py",
    "src/to_model/intent/train.py",
    "src/to_model/intent/predict.py",
    "src/to_model/intent/evaluation.py",
    "src/to_model/reasoning/__init__.py",
    "src/to_model/reasoning/task_planner.py",
    "src/to_model/reasoning/decision_policy.py",
    "src/to_model/reasoning/result_analyzer.py",
    "src/to_model/training/__init__.py",
    "src/to_model/training/dataset_loader.py",
    "src/to_model/training/data_collator.py",
    "src/to_model/training/trainer.py",
    "src/to_model/training/loss.py",
    "src/to_model/training/optimizer.py",
    "src/to_model/training/checkpoint.py",
    "src/to_model/training/resume_training.py",
    "src/to_model/inference/__init__.py",
    "src/to_model/inference/model_loader.py",
    "src/to_model/inference/inference_engine.py",
    "src/to_model/inference/sampling.py",
    "src/to_model/evaluation/__init__.py",
    "src/to_model/evaluation/benchmark.py",
    "src/to_model/evaluation/classification_metrics.py",
    "src/to_model/evaluation/generation_metrics.py",
    "src/to_model/evaluation/regression_tests.py",
    "src/to_model/safety/__init__.py",
    "src/to_model/safety/output_validator.py",
    "src/to_model/safety/tool_call_validator.py",
    "src/to_model/safety/medical_safety_guard.py",
    "src/to_model/common/__init__.py",
    "src/to_model/common/logging_config.py",
    "src/to_model/common/exceptions.py",
    "src/to_model/common/version.py",
    "scripts/train_llm.py",
    "scripts/train_intent.py",
    "scripts/evaluate.py",
    "scripts/export_model.py",
    "tests/test_tokenizer.py",
    "tests/test_llm.py",
    "tests/test_intent_model.py",
    "tests/test_grammar_reference.py",
    "tests/test_training.py",
    "tests/test_api.py",
]


def create_to_model_app(root_path: str = "to-model-app") -> None:
    base = Path(root_path)
    for d in DIRECTORIES:
        (base / d).mkdir(parents=True, exist_ok=True)

    for f in FILES:
        fp = base / f
        if fp.exists():
            continue
        if f.endswith(".json"):
            fp.write_text(json.dumps({"_file": f, "version": "0.1.0"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif f == ".gitignore":
            fp.write_text(
                "__pycache__/\n*.py[cod]\n.venv/\nartifacts/checkpoints/*\n!artifacts/checkpoints/.gitkeep\ndatasets/raw/*\n",
                encoding="utf-8",
            )
        elif f == "pyproject.toml":
            fp.write_text(
                '[project]\nname = "to-model"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n\n'
                '[tool.pytest.ini_options]\npythonpath = ["src"]\n',
                encoding="utf-8",
            )
        else:
            fp.write_text(f"# {f}\n", encoding="utf-8")

    print(f"✅ `to-model-app/` のディレクトリ構造（{len(DIRECTORIES)} フォルダ / {len(FILES)} ファイル）を生成しました: {base.resolve()}")


if __name__ == "__main__":
    create_to_model_app()
