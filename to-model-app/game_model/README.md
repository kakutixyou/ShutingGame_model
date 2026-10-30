# Game Model

このフォルダには、シューティングゲーム向けの設定モデルを JSON で定義しています。

- `game_session_template.json`: ゲーム全体のテンプレート
- `item_library.json`: アイテム定義と効果一覧
- `player_profile.json`: プレイヤーの初期値と調整項目
- `boss_profile.json`: ボス敵のHPと戦闘設定

主な初期値:
- アイテムドロップ間隔: 3 秒
- ボスHP: 200
- 残機: 2
- 攻撃力UP: 永続 +3
- ダメージ無効化: 10 秒間、全ダメージ null
