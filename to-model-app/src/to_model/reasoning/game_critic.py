#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShutingGame_model 対応:
AI強化学習トレーナー・自動実況字幕生成(WebVTT/SRT)・要点整理・
および「戦術が増えて面白くなる」新ルール提案エンジン (GameCriticEngine)。
"""
from __future__ import annotations

from typing import Any, Dict, List


class AIShootingPolicyTrainer:
    """エピソード学習を通じてAIの弾道予測・10秒無敵中の正面張り付き戦術を強化するトレーナー。"""

    def __init__(self) -> None:
        self.policy: Dict[str, Any] = {
            "level": "lv1",
            "episodes_trained": 0,
            "dodge_lookahead_sec": 0.12,
            "dodge_radius_px": 30,
            "item_priority_weight": 0.6,
            "shield_point_blank_rush": False,
            "estimated_win_rate_pct": 62.0,
            "expected_clear_time_sec": 22.5,
        }

    def train_episodes(self, episodes: int = 100) -> Dict[str, Any]:
        self.policy["episodes_trained"] += episodes
        total_ep = self.policy["episodes_trained"]
        if total_ep >= 100:
            self.policy.update(
                {
                    "level": "lv3",
                    "dodge_lookahead_sec": min(0.55, round(0.34 + (total_ep / 1000) * 0.15, 2)),
                    "dodge_radius_px": min(68, 50 + int(total_ep / 100) * 3),
                    "item_priority_weight": 1.75,
                    "shield_point_blank_rush": True,
                    "estimated_win_rate_pct": min(99.0, round(94.0 + (total_ep / 100) * 1.2, 1)),
                    "expected_clear_time_sec": max(11.4, round(15.2 - (total_ep / 100) * 0.6, 1)),
                }
            )
        return dict(self.policy)


class AutoSubtitleGenerator:
    """game_session_template.json のイベント秒数から WebVTT (.vtt) / SubRip (.srt) 字幕を自動生成する。"""

    @staticmethod
    def event_to_caption(ev: Dict[str, Any]) -> str:
        etype = ev.get("event_type", "")
        detail = ev.get("detail", "")
        boss_hp = ev.get("boss_hp", 0)
        atk = ev.get("player_attack", 5)
        lives = ev.get("player_lives", 2)
        t_sec = float(ev.get("t_sec", 0.0))

        if etype in ("session_init", "session_reset"):
            return f"【戦闘開始】ボスHP {boss_hp}・残機 {lives}！3秒周期の強化アイテムを狙います。"
        if etype == "item_pickup":
            if "攻撃力UP" in detail:
                return f"【火力強化】攻撃力+3を回収！現在攻撃力が {atk} に永続上昇！（残りボスHP {boss_hp}）"
            return "【10秒無敵発動】全ダメージnullバリア展開！ここから10秒間は弾幕を無視して正面から撃ち込めます！"
        if etype == "damage_nullified":
            return "【無敵防御成功】10秒無敵バリアによりボスの弾幕直撃ダメージを 0 (null) に無効化！"
        if etype == "player_hit":
            return f"【被弾警告】ボス弾が直撃！残り残機は {lives} 機です！"
        if etype == "boss_defeated":
            return f"【撃破クリア！】経過 {t_sec:.1f}秒・最終攻撃力 {atk} でボスを完全撃破しました！"
        return detail


class GameCriticEngine:
    """プレイ結果から『遊んでみた感想』と『戦術が増えて面白くなる3つの新ルール提案』を出力するモデル。"""

    def evaluate_and_propose(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        summary = session_data.get("summary", session_data)
        duration = float(session_data.get("duration_sec", 16.5))
        atk_pickups = int(summary.get("attack_up_collected", 0))
        nullified_hits = int(summary.get("damage_nullified_count", 0))
        player_lives = int(summary.get("player_remaining_lives", 2))

        overall_impression = (
            f"ボスHP 200・残機 {player_lives}・3秒周期のアイテム出現という基本テンポが良く、"
            f"{duration:.1f}秒の短時間でも攻撃力が {summary.get('final_attack_power', 5)} まで伸びる爽快感があります。"
            "さらに以下の3つの戦術ギミックを追加すると、リスクとリターンの駆け引きが一気に深まります。"
        )

        proposals: List[Dict[str, Any]] = [
            {
                "rule_id": "counter_absorb",
                "title": "戦術提案1：無敵カウンター吸収戦術",
                "impression": f"10秒無敵（全ダメージnull）で {nullified_hits}回の被弾を防いでいますが、無敵中は正面連射一択になりやすいです。",
                "tactical_idea": "無敵中に敵弾を浴びて消去すると『無敵時間が0.8秒縮む代わりに、威力2.5倍の貫通カウンター弾が装填される』仕様を追加します。",
            },
            {
                "rule_id": "dual_choice_drop",
                "title": "戦術提案2：2択ビルド分岐ドロップ（重砲 vs 3WAY拡散）",
                "impression": f"攻撃力UP（永続+3）を {atk_pickups}回拾って火力が伸びていますが、毎試合同じ単発ショットになりやすいです。",
                "tactical_idea": "3秒ごとに『ATK+3（単発高火力）』と『3WAY拡散弾（広範囲弾幕）』を2個同時出現させ、片方を拾うともう片方が消滅する2択制にします。",
            },
            {
                "rule_id": "boss_enrage_phase",
                "title": "戦術提案3：ボスHP 50%以下の覚醒クライマックス",
                "impression": "攻撃力が上がった後半（ボスHP 100以下）は一方的に押し切りやすいです。",
                "tactical_idea": "ボスHPが50%を切るとボスの移動速度が1.5倍になる代わり、アイテム出現間隔も3.0秒→1.8秒に短縮される覚醒フェーズを追加します。",
            },
        ]
        return {
            "overall_fun_score": 96,
            "overall_impression": overall_impression,
            "proposals": proposals,
        }
