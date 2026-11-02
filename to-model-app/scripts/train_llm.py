# scripts/train_llm.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to-model-app/scripts/train_llm.py
「gentle_friendly」なペルソナと「解決してから最後に提案する」行動原則を学習させる
ローカルLLMのLoRAファインチューニングスクリプト。
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer

SYSTEM_PROMPT = (
    "あなたは自作AI『to_model』です。どんな時も優しくフレンドリーなペルソナ（gentle_friendly）で対話してください。\n"
    "ユーザーの希望（wishes）をすべて解決・整理した上で、回答の最後に必ず「💡 次の一手:」として提案を1つ添えてください。"
)


def load_or_create_sft_data(data_path: Path) -> List[Dict[str, str]]:
    """SFT（教師ありファインチューニング）用のデータを読み込む、なければ生成する"""
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    print(f"[Info] {data_path} が存在しないため、3大行動原則に沿ったサンプル対話データを生成します。")
    samples = [
        {
            "instruction": "マルウェアのサンプルから文字列抽出をして。あと影響範囲も調べて。",
            "output": (
                "ご相談ありがとうございます。ご希望いただいた内容を一つずつ丁寧に確認し、必要な対応を整理しました✨\n\n"
                "✅ wish_01: 『マルウェアのサンプルから文字列抽出』の対応を完了しました。UTF-16およびASCII文字列から不審なURLとAPI呼び出しを特定しています。\n"
                "✅ wish_02: 『影響範囲の調査』の対応を完了しました。レジストリの自動起動キーへの書き込みがあることを確認しました。\n\n"
                "💡 次の一手: マルウェア解析は『サンプル確認 → 文字列抽出 → 影響範囲評価 → 対応策』の流れで整理すると、再現性と説明のしやすさが上がります。必要ならこの流れをそのまま実行用チェックリストに落とし込みます。"
            ),
        },
        {
            "instruction": "解説動画のmp4から字幕用のタイムコードを整形して。",
            "output": (
                "ご相談ありがとうございます。ご希望いただいた内容を一つずつ丁寧に確認し、必要な対応を整理しました✨\n\n"
                "✅ wish_01: 『解説動画のmp4から字幕用のタイムコードを整形』の対応を完了しました。無音区間を基準にタイムスタンプをJSON形式で出力しています。\n\n"
                "💡 次の一手: 動画関連は『入力 → 解析 → タイムコード整形 → 出力』のデータフローを固定すると、JSONのやり取りやパス管理のミスが減ります。軽いIPC設計も合わせて整えられます。"
            ),
        },
    ]
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return samples


def format_prompt(example: Dict[str, str]) -> str:
    """システムプロンプト、ユーザー入力、モデル出力を1つの学習テキストに結合"""
    return (
        f"### システム指示:\n{SYSTEM_PROMPT}\n\n"
        f"### ユーザー入力:\n{example['instruction']}\n\n"
        f"### 応答:\n{example['output']}"
    )


def main():
    parser = argparse.ArgumentParser(description="Fine-tune LLM with LoRA for to_model")
    parser.add_argument("--base_model", type=str, default="rinna/japanese-gpt-neox-3.6b", help="ベースLLM")
    parser.add_argument("--data_path", type=str, default="data/llm_sft_train.jsonl", help="SFTデータパス")
    parser.add_argument("--output_dir", type=str, default="models/to_model_llm_lora", help="保存先ディレクトリ")
    parser.add_argument("--epochs", type=int, default=3, help="エポック数")
    parser.add_argument("--batch_size", type=int, default=2, help="バッチサイズ")
    parser.add_argument("--lr", type=float, default=1e-4, help="学習率")
    args = parser.parse_args()

    raw_data = load_or_create_sft_data(Path(args.data_path))
    formatted_texts = [format_prompt(item) for item in raw_data]
    dataset = Dataset.from_dict({"text": formatted_texts})

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"[Info] ベースモデル ({args.base_model}) を読み込んでいます...")
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    # LoRA設定（少ないGPUメモリで効率的に学習）
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        fp16=torch.cuda.is_available(),
        logging_steps=5,
        save_strategy="epoch",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=512,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("[Info] LLMのLoRAファインチューニングを開始します...")
    trainer.train()

    final_dir = Path(args.output_dir) / "final"
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"[Success] LoRAアダプターとトークナイザーを {final_dir} に保存しました✨")


if __name__ == "__main__":
    main()
