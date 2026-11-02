#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
to-model-app/scripts/train_intent.py
ユーザー入力からメッセージタイプ（greeting, self_intro, task, unclear）を分類する
軽量エンコーダーモデル（Intent Classifier）の学習スクリプト。
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

import torch
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

LABEL2ID: Dict[str, int] = {
    "greeting": 0,
    "self_intro": 1,
    "task": 2,
    "unclear": 3,
}
ID2LABEL: Dict[int, str] = {v: k for k, v in LABEL2ID.items()}


def load_or_create_dummy_data(data_path: Path) -> List[Dict[str, str]]:
    """データセットが存在しない場合、実践的な初期ダミーデータを生成して返す"""
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    print(f"[Info] {data_path} が見つかりません。初期学習用のサンプルデータを自動生成します。")
    dummy_samples = [
        {"text": "こんにちは！今日もいい天気ですね。", "label": "greeting"},
        {"text": "おはようございます。調子はどう？", "label": "greeting"},
        {"text": "いつもありがとう、またね！", "label": "greeting"},
        {"text": "あなたの自己紹介をしてください。", "label": "self_intro"},
        {"text": "どんなAIなのか、何ができるのか教えて。", "label": "self_intro"},
        {"text": "今何%くらい出来上がってるの？自己解析して。", "label": "self_intro"},
        {"text": "このマルウェアの検体から文字列を抽出して解析して。", "label": "task"},
        {"text": "mp4動画のタイムコードを整形して字幕JSONを作って。", "label": "task"},
        {"text": "シューティングゲームの自機の移動速度を修正してほしい。", "label": "task"},
        {"text": "tools.batを動かしてIPC通信のチェックをお願い。", "label": "task"},
        {"text": "あー、なんかアレがこうしてね。", "label": "unclear"},
        {"text": "うーん、どうしようかな。", "label": "unclear"},
    ]
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        for sample in dummy_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return dummy_samples


def main():
    parser = argparse.ArgumentParser(description="Train Intent Classification Model for to_model")
    parser.add_argument("--model_name", type=str, default="cl-tohoku/bert-base-japanese-v3", help="ベースモデル名")
    parser.add_argument("--data_path", type=str, default="data/intent_train.jsonl", help="学習データパス")
    parser.add_argument("--output_dir", type=str, default="models/intent_classifier", help="モデル保存先")
    parser.add_argument("--epochs", type=int, default=5, help="エポック数")
    parser.add_argument("--batch_size", type=int, default=8, help="バッチサイズ")
    parser.add_argument("--lr", type=float, default=2e-5, help="学習率")
    args = parser.parse_args()

    raw_data = load_or_create_dummy_data(Path(args.data_path))

    # Datasetの構築
    dataset_dict = {
        "text": [item["text"] for item in raw_data],
        "label": [LABEL2ID.get(item["label"], 3) for item in raw_data],
    }
    dataset = Dataset.from_dict(dataset_dict)
    dataset = dataset.train_test_split(test_size=0.2, seed=42)

    # トークナイザーとモデルの準備
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    def tokenize_fn(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

    tokenized_datasets = dataset.map(tokenize_fn, batched=True)

    # 学習設定
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        load_best_model_at_end=True,
        logging_steps=10,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["test"],
        tokenizer=tokenizer,
    )

    print("[Info] 意図分類モデルの学習を開始します...")
    trainer.train()

    # 最終モデルの保存
    final_path = Path(args.output_dir) / "final"
    trainer.save_model(str(final_path))
    tokenizer.save_pretrained(str(final_path))
    print(f"[Success] 意図分類モデルを {final_path} に保存しました✨")


if __name__ == "__main__":
    main()
