# 日本株デイトレード戦略モード仕様書 v1.0

## 0. 重要な前提

本仕様書は、日本株の1分足・日足データを使って、デイトレード手法を安全なシミュレーター内で検証するための仕様書である。

本仕様書の目的は、特定の銘柄を推奨することでも、実際の投資判断を助言することでもない。過去データを用いたルールベース戦略の検証を目的とする。

デイトレードは短時間で損益が大きく変動しやすく、特に信用取引・レバレッジ・過度な売買回数は損失リスクを高める。そのため、本システムでは以下を最優先する。

- 取引回数を制限する
- 損切りを必ず設定する
- 1回あたりの損失を小さくする
- 1日の最大損失に達したら停止する
- 大引け前に必ず全決済する
- 検証結果が安定するまでは実売買に接続しない

本仕様書では、経験豊富な日本株デイトレーダーが一般に重視する「無理に入らない」「損切りを早くする」「強い銘柄だけ触る」「需給とVWAPを重視する」「一日の負け上限を決める」という考え方を、機械的に検証できるルールへ落とし込む。

---

## 1. 実装する戦略モード

本システムでは、以下の4種類の戦略モードを実装する。

### 1.1 要素別手法モード

個別の売買要素を単独で検証するモード。

目的は、各シグナルが単体でどれくらい機能するかを調べることである。

例：

- VWAP上抜け買い
- VWAP反発買い
- 移動平均線上抜け買い
- 直近高値ブレイク買い
- ボリンジャーバンド3σ逆張り
- ボリンジャーバンド3σ到達後の利確
- 前日高値ブレイク
- 前日安値割れ回避
- 出来高急増ブレイク

### 1.2 低リスク手法モード

複数の低リスク寄り条件がそろった場合のみエントリーするモード。

特徴：

- 買い専用
- 取引回数は少ない
- VWAPより上の銘柄だけ触る
- 押し目を待つ
- 損切りを浅くする
- 日次損失制限を厳しくする

初心者が最初に検証するべきメインモードとする。

### 1.3 通常手法モード

低リスク手法よりも少し積極的に、ブレイクアウトや出来高急増を取りにいくモード。

特徴：

- 買い専用を基本とする
- VWAP上での高値ブレイクを狙う
- 押し目買いだけでなく、順張りブレイクも許可する
- 損切りは必須
- 取引回数は中程度

### 1.4 ややリスクのある手法モード

よりハイリスク・ハイリターンな場面を検証するモード。

特徴：

- 急騰初動・高値更新・出来高急増に乗る
- 条件付きでボリンジャーバンド上限付近のモメンタム継続も許可する
- 条件付きで空売り・逆張りも検証可能にする
- ただし実売買接続時は初期状態で無効化する

---

## 2. 共通データ仕様

### 2.1 1分足データ

必須列：

```csv
timestamp,open,high,low,close,volume
```

例：

```csv
2026-06-24 09:00:00,90200,91500,89800,91000,120000
```

### 2.2 日足データ

必須列：

```csv
date,open,high,low,close,volume
```

### 2.3 価格単位

日本株の価格は円で扱う。

実データを使用し、サンプル価格を本番検証に混入させてはならない。

異常値チェック：

- close が 0 以下ならエラー
- high < low ならエラー
- open, high, low, close のいずれかが欠損ならエラー
- volume が負ならエラー
- 同一銘柄・同一日付で価格水準が前後日比で極端に乖離する場合は警告

---

## 3. 共通指標

全モードで以下の指標を計算する。

### 3.1 VWAP

1分足ベースの近似VWAPを用いる。

```text
typical_price = (high + low + close) / 3
vwap = cumulative_sum(typical_price * volume) / cumulative_sum(volume)
```

### 3.2 移動平均線

1分足：

- MA5
- MA25
- MA75

日足：

- DMA5
- DMA25
- DMA75

### 3.3 ボリンジャーバンド

1分足終値ベースで計算する。

標準設定：

- window = 20
- sigma = 2
- sigma = 3

計算値：

- bb_mid
- bb_upper_2
- bb_lower_2
- bb_upper_3
- bb_lower_3

### 3.4 出来高指標

- volume_ma5
- volume_ma25
- volume_ratio_5_to_25 = volume_ma5 / volume_ma25
- recent_5min_volume
- avg_30min_volume

---

## 4. 共通リスク管理

全モードに必ず適用する。

### 4.1 ポジション制限

初期実装では同時保有ポジションは1つまで。

```text
position_state:
- FLAT
- LONG
- SHORT
```

### 4.2 1回あたり最大損失

初期値：

```text
max_loss_per_trade_pct = 0.3%
```

### 4.3 日次最大損失

低リスクモード：

```text
max_daily_loss_pct = 0.5%
```

通常モード：

```text
max_daily_loss_pct = 1.0%
```

ややリスクありモード：

```text
max_daily_loss_pct = 1.5%
```

日次最大損失に達したら、その日は新規エントリーを停止する。

### 4.4 最大取引回数

低リスクモード：

```text
max_trades_per_day = 3
```

通常モード：

```text
max_trades_per_day = 5
```

ややリスクありモード：

```text
max_trades_per_day = 8
```

### 4.5 連敗停止

```text
max_consecutive_losses = 3
```

3連敗したら、その日は新規エントリーを停止する。

### 4.6 時間制限

原則：

- 09:00〜09:05 は新規エントリー禁止
- 11:25 以降、前場の新規エントリー禁止
- 12:30〜12:35 は新規エントリー禁止
- 14:45 以降、新規エントリー禁止
- 14:50 以降、全ポジションを強制決済

将来的に、寄り直後専用モードを別途検証してもよいが、低リスクモードでは寄り直後を避ける。

---

## 5. 要素別手法モード

個別シグナルを単体で検証する。

各要素別手法は、以下の共通インターフェースを持つ。

```python
class SignalStrategy:
    name: str
    direction: Literal["long", "short", "both"]
    risk_level: Literal["low", "normal", "high"]

    def should_enter(context) -> bool:
        ...

    def should_exit(context, position) -> bool:
        ...
```

---

### 5.1 VWAP上抜け買い

#### 目的

価格がVWAPを下から上抜けたタイミングで買う。

#### エントリー条件

```text
previous_close <= previous_vwap
current_close > current_vwap
current_close > MA5
MA5 >= MA25
volume_ratio_5_to_25 >= 1.0
```

#### 除外条件

```text
current_close < previous_day_low
current_time < 09:05
current_time > 14:45
```

#### 決済条件

```text
current_close < VWAP
or current_close <= entry_price * 0.997
or current_close >= entry_price * 1.005
or current_time >= 14:50
```

---

### 5.2 VWAP反発買い

#### 目的

当日強い銘柄がVWAP付近まで押したあと、再上昇する局面を狙う。

#### エントリー条件

```text
current_close > VWAP
MA5 > MA25
MA25 is rising
直近30分以内に当日高値更新がある
current_low <= VWAP * 1.002
current_close > previous_5min_high
volume_ratio_5_to_25 >= 1.0
```

#### 決済条件

```text
current_close < VWAP
or current_close <= entry_price * 0.997
or current_close >= entry_price * 1.006
or current_close < MA5 after unrealized_profit >= 0.4%
or current_time >= 14:50
```

#### リスク評価

低リスク。

---

### 5.3 MA5/MA25上抜け買い

#### エントリー条件

```text
MA5 crosses above MA25
current_close > VWAP
current_close > MA5
volume_ratio_5_to_25 >= 1.0
```

#### 決済条件

```text
MA5 crosses below MA25
or current_close < VWAP
or stop_loss
or take_profit
```

#### リスク評価

通常。

---

### 5.4 直近高値ブレイク買い

#### エントリー条件

```text
current_close > highest_high_last_30min
current_close > VWAP
MA5 > MA25
volume_ratio_5_to_25 >= 1.2
```

#### 決済条件

```text
current_close < breakout_level
or current_close < MA5
or current_close <= entry_price * 0.996
or current_close >= entry_price * 1.008
or current_time >= 14:50
```

#### リスク評価

通常〜やや高リスク。

---

### 5.5 前日高値ブレイク買い

#### エントリー条件

```text
current_close > previous_day_high
current_close > VWAP
MA5 > MA25
volume_ratio_5_to_25 >= 1.2
```

#### 決済条件

```text
current_close < previous_day_high
or current_close < MA5
or stop_loss
or take_profit
```

#### リスク評価

通常。

---

### 5.6 出来高急増ブレイク買い

#### エントリー条件

```text
current_close > highest_high_last_15min
recent_5min_volume > avg_30min_volume * 1.5
current_close > VWAP
MA5 > MA25
```

#### 決済条件

```text
current_close < MA5
or current_close < VWAP
or stop_loss
or trailing_stop
```

#### リスク評価

やや高リスク。

---

### 5.7 ボリンジャーバンド+3σ逆張り売り

#### 重要注意

この手法は単独では危険である。強い上昇トレンドでは+3σを超えたあとも上昇が継続することがある。

したがって、初期状態では実売買向けには無効化し、シミュレーター上の要素別検証のみ許可する。

#### エントリー条件

```text
current_close > bb_upper_3
current_close < previous_close
current_close < current_open  # 陰線
volume_ratio_5_to_25 < 1.2  # 出来高が過熱継続していない
current_close is far above VWAP by >= 1.5%
```

#### 決済条件

```text
current_close <= bb_upper_2
or current_close <= MA5
or current_close >= entry_price * 1.003  # 空売り損切り
or current_time >= 14:50
```

#### リスク評価

高リスク。

---

### 5.8 ボリンジャーバンド+3σ到達後の利確

#### 目的

新規空売りではなく、買いポジションの利確条件として使う。

#### 条件

```text
position == LONG
current_close > bb_upper_3
```

この時点で `overheat_mode = True` にする。

その後、以下のいずれかで利確：

```text
overheat_mode == True and current_close < current_open
or current_close < previous_low
or current_close < MA5
```

#### リスク評価

低〜通常。

---

## 6. 低リスク手法モード

### 6.1 コンセプト

「強い日に、強い銘柄で、VWAPより上にいる状態で、押し目だけ買う」。

高値を追いかけず、VWAPやMA5付近まで押してから再上昇する場面を狙う。

### 6.2 日足フィルター

以下をすべて満たす場合のみ当日取引を許可する。

```text
previous_close > DMA25
DMA5 >= DMA25 or DMA25 is rising
previous_day_volume >= average_volume_20d * 0.8
current_open >= previous_close * 0.98
current_open <= previous_close * 1.05
```

極端なギャップアップは避ける。

```text
current_open > previous_close * 1.08 の場合は取引禁止
```

### 6.3 1分足エントリー条件

```text
current_close > VWAP
MA5 > MA25
MA25 is rising
直近30分以内に当日高値更新がある
current_low <= min(VWAP * 1.002, MA5 * 1.002)
current_close > previous_5min_high
volume_ratio_5_to_25 >= 1.0
```

### 6.4 決済条件

損切り：

```text
current_close <= entry_price * 0.997
or current_close < VWAP * 0.999
or current_close < recent_swing_low
```

利確：

```text
current_close >= entry_price * 1.005
```

利益保護：

```text
unrealized_profit >= 0.4% になったら stop を entry_price に引き上げる
```

トレーリング：

```text
unrealized_profit >= 0.5% の後、current_close < MA5 で決済
```

時間決済：

```text
current_time >= 14:50 で全決済
```

### 6.5 リスク設定

```text
max_trades_per_day = 3
max_daily_loss_pct = 0.5%
max_loss_per_trade_pct = 0.3%
allow_short = False
allow_averaging_down = False
```

---

## 7. 通常手法モード

### 7.1 コンセプト

VWAP上の押し目買いに加えて、直近高値ブレイク・前日高値ブレイクも狙う。

### 7.2 日足フィルター

```text
previous_close > DMA25
current_open >= previous_close * 0.97
current_open <= previous_close * 1.08
previous_day_volume >= average_volume_20d * 0.7
```

### 7.3 エントリー候補

以下のいずれかを満たしたらエントリー候補。

#### A. VWAP反発買い

低リスクモードと同じ。

#### B. 直近高値ブレイク

```text
current_close > highest_high_last_30min
current_close > VWAP
MA5 > MA25
volume_ratio_5_to_25 >= 1.2
```

#### C. 前日高値ブレイク

```text
current_close > previous_day_high
current_close > VWAP
MA5 > MA25
volume_ratio_5_to_25 >= 1.2
```

### 7.4 決済条件

```text
stop_loss = -0.4%
take_profit = +0.8%
VWAP割れで撤退
MA5割れで利益確定または撤退
BB+3σ到達後に陰線で利確
14:50で全決済
```

### 7.5 リスク設定

```text
max_trades_per_day = 5
max_daily_loss_pct = 1.0%
max_loss_per_trade_pct = 0.4%
allow_short = False
allow_averaging_down = False
```

---

## 8. ややリスクのある手法モード

### 8.1 コンセプト

出来高急増・高値ブレイク・強いモメンタム継続を狙う。

成功時の値幅は大きいが、高値掴み・急反落のリスクが高い。

### 8.2 日足フィルター

```text
current_open >= previous_close * 0.95
current_open <= previous_close * 1.12
previous_day_volume >= average_volume_20d * 0.5
```

### 8.3 エントリー候補

#### A. 出来高急増ブレイク

```text
current_close > highest_high_last_15min
recent_5min_volume > avg_30min_volume * 1.5
current_close > VWAP
MA5 > MA25
```

#### B. 前日高値ブレイク

```text
current_close > previous_day_high
volume_ratio_5_to_25 >= 1.5
current_close > VWAP
```

#### C. BB+2σモメンタム継続

```text
current_close > bb_upper_2
current_close < bb_upper_3
MA5 > MA25
current_close > VWAP
volume_ratio_5_to_25 >= 1.3
```

### 8.4 条件付き逆張りショート

初期実装ではバックテスト専用。

```text
allow_short_backtest_only = True
allow_short_live = False
```

条件：

```text
current_close > bb_upper_3
current_close < current_open
current_close < previous_close
volume_ratio_5_to_25 < 1.2
current_close >= VWAP * 1.015
```

### 8.5 決済条件

```text
stop_loss = -0.5%
take_profit = +1.0%
利益が +0.6% を超えたらトレーリング開始
直近5分安値割れで決済
VWAP割れで撤退
14:50で全決済
```

### 8.6 リスク設定

```text
max_trades_per_day = 8
max_daily_loss_pct = 1.5%
max_loss_per_trade_pct = 0.5%
allow_averaging_down = False
```

---

## 9. 利確ロジック仕様

### 9.1 固定利確

各モードで固定利確を設定する。

```text
低リスク: +0.5%
通常: +0.8%
ややリスクあり: +1.0%
```

### 9.2 建値撤退

含み益が一定以上になった場合、損切りラインを建値に引き上げる。

```text
低リスク: +0.4% 到達で建値撤退
通常: +0.5% 到達で建値撤退
ややリスクあり: +0.6% 到達で建値撤退
```

### 9.3 トレーリング

一定以上の含み益が出た後は、以下で決済する。

```text
current_close < MA5
or current_close < recent_5min_low
or current_close < VWAP
```

### 9.4 ボリンジャーバンド利確

```text
LONG保有中に current_close > bb_upper_3 なら overheat_mode = True
その後、陰線 or MA5割れ or 直近安値割れで利確
```

---

## 10. 実験・比較仕様

### 10.1 実験対象

任意の銘柄・任意の日付範囲に対して、以下を比較できるようにする。

```text
- element_vwap_cross
- element_vwap_pullback
- element_ma_cross
- element_recent_high_breakout
- element_previous_day_high_breakout
- element_volume_breakout
- element_bb3_reversal_short
- element_bb3_take_profit
- combined_low_risk
- combined_normal
- combined_high_risk
```

### 10.2 CLI例

```bash
python scripts/backtest.py \
  --symbol 285A \
  --start-date 2026-06-01 \
  --end-date 2026-06-30 \
  --mode combined_low_risk
```

複数モード比較：

```bash
python scripts/compare_strategies.py \
  --symbol 285A \
  --start-date 2026-06-01 \
  --end-date 2026-06-30 \
  --modes element_vwap_pullback combined_low_risk combined_normal combined_high_risk
```

### 10.3 評価指標

必須出力：

```text
総損益
勝率
平均利益
平均損失
期待値
最大ドローダウン
プロフィットファクター
総トレード回数
1日平均トレード回数
最大連敗数
日次最大損失
時間帯別成績
銘柄別成績
モード別成績
```

### 10.4 重要な比較観点

単に総利益が大きいものを良い戦略としない。

以下を重視する。

```text
最大ドローダウンが小さい
平均損失が小さい
連敗時の損失が限定されている
取引回数が過剰でない
特定の1日だけで利益が出ていない
複数日・複数銘柄で再現性がある
```

---

## 11. 実装ファイル構成案

```text
src/
  strategies/
    base.py
    element_vwap_cross.py
    element_vwap_pullback.py
    element_ma_cross.py
    element_recent_high_breakout.py
    element_previous_day_high_breakout.py
    element_volume_breakout.py
    element_bb3_reversal_short.py
    element_bb3_take_profit.py
    combined_low_risk.py
    combined_normal.py
    combined_high_risk.py
  indicators/
    vwap.py
    moving_average.py
    bollinger.py
    volume.py
  simulator/
    broker.py
    order.py
    position.py
    risk_manager.py
    backtest_engine.py
  data/
    loader.py
    validator.py
  reports/
    metrics.py
    plots.py
scripts/
  backtest.py
  compare_strategies.py
  download_data.py
```

---

## 12. StrategyConfig仕様

各戦略は設定値を外部から変更できるようにする。

```python
@dataclass
class StrategyConfig:
    mode: str
    stop_loss_pct: float
    take_profit_pct: float
    break_even_trigger_pct: float
    trailing_start_pct: float
    max_daily_loss_pct: float
    max_trades_per_day: int
    max_consecutive_losses: int
    allow_short: bool
    allow_averaging_down: bool
    entry_start_time: str
    entry_end_time: str
    force_exit_time: str
```

---

## 13. デフォルト設定

### 13.1 低リスク

```yaml
mode: combined_low_risk
stop_loss_pct: 0.003
take_profit_pct: 0.005
break_even_trigger_pct: 0.004
trailing_start_pct: 0.005
max_daily_loss_pct: 0.005
max_trades_per_day: 3
max_consecutive_losses: 3
allow_short: false
allow_averaging_down: false
entry_start_time: "09:05"
entry_end_time: "14:45"
force_exit_time: "14:50"
```

### 13.2 通常

```yaml
mode: combined_normal
stop_loss_pct: 0.004
take_profit_pct: 0.008
break_even_trigger_pct: 0.005
trailing_start_pct: 0.006
max_daily_loss_pct: 0.010
max_trades_per_day: 5
max_consecutive_losses: 3
allow_short: false
allow_averaging_down: false
entry_start_time: "09:05"
entry_end_time: "14:45"
force_exit_time: "14:50"
```

### 13.3 ややリスクあり

```yaml
mode: combined_high_risk
stop_loss_pct: 0.005
take_profit_pct: 0.010
break_even_trigger_pct: 0.006
trailing_start_pct: 0.006
max_daily_loss_pct: 0.015
max_trades_per_day: 8
max_consecutive_losses: 3
allow_short: false
allow_averaging_down: false
entry_start_time: "09:05"
entry_end_time: "14:45"
force_exit_time: "14:50"
```

---

## 14. 禁止事項

初期実装では以下を禁止する。

```text
ナンピン
マーチンゲール
損切りなし
日をまたいだ持ち越し
複数ポジション同時保有
負けた後のロット増加
実売買APIへの自動接続
```

---

## 15. 実売買接続前の必須条件

実売買APIに接続する前に、最低限以下を満たす必要がある。

```text
最低3か月以上の過去データで検証
複数銘柄で検証
手数料・スリッページ込みで検証
最大ドローダウンが許容範囲内
日次損失制限が正しく動作
異常データ時に停止する
注文重複送信を防止する
API切断時に停止する
想定外ポジション検出時に停止する
paper tradingで安定動作を確認
```

---

## 16. まとめ

本仕様書では、個別のデイトレード要素を単体で検証するモードと、それらを組み合わせた3段階のリスク別モードを定義した。

最初に実装・検証すべき順序は以下。

```text
1. element_vwap_pullback
2. element_vwap_cross
3. element_recent_high_breakout
4. element_bb3_take_profit
5. combined_low_risk
6. combined_normal
7. combined_high_risk
8. element_bb3_reversal_short
```

最初の本命は `combined_low_risk` とする。

このモードは、VWAPより上の強い銘柄で押し目を待ち、浅い損切りと日次損失制限を徹底する。利益最大化よりも、損失を小さく保ちながら再現性を検証することを優先する。
