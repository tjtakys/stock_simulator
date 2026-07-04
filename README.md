# デイトレード練習・自動売買アルゴリズム検証シミュレーター

PC上で動作するPython製のデイトレード練習・ルールベース戦略検証シミュレーターです。初期版は、過去データだけを使う安全なシミュレーションに限定し、実売買APIには接続しません。

本プロジェクトは OpenAI Codex を使って設計・実装を進めています。追加要望が入った場合は、実装とあわせて [仕様書](docs/APP_SPEC.md) も更新します。

## 機能

- キオクシアホールディングス `285A` のサンプル1分足・日足データ生成
- Yahooファイナンスからの実データ取得
- 1分足、3分足、5分足、10分足、30分足、60分足、日足、週足、月足の表示
- 未来情報を見せないReplayEngine
- 入金額ベースの成行仮想約定、ロング・ショート、買い増し/売り増し、決済、損益計算
- 出来高加重平均価格、移動平均線、ボリンジャーバンド（±1σ/±2σ/±3σ）
- Streamlitによる手動デイトレード練習UI
- 過去10分/30分/60分の分足チャート、自動再生、銘柄コード・日付の自由入力
- 実データ取得中の表示、約定通知、チャート上の売買マーカー
- 起動時の日足ネックライン設定と、各分足チャートへの常時表示
- 再生 / 一時停止ボタン
- VWAP+MA、ボリンジャー逆張り、複合ルール戦略
- CLIバックテストとHTML/CSVレポート出力
- pytestによる基本テスト

## セットアップ

```bash
conda env create -f environment.yml
conda activate sim
```

既存環境に入れる場合:

```bash
pip install -r requirements.txt
```

## Streamlit UI

```bash
conda activate sim
streamlit run app.py
```

デフォルトではYahooファイナンスから実データを取得します。東証銘柄は、例として `285A` を入力すると内部で `285A.T` として取得します。

実データの取得先:

```text
data/raw/yahoo/minute/
data/raw/yahoo/daily/
```

サンプルモードを選ぶと、`data/raw/minute/` と `data/raw/daily/` にサンプルCSVが無ければ自動生成します。

起動後は、まず日足チャートでサポートライン、レジスタンスライン、直近高値、移動平均線、ボリンジャーバンドなどのネックラインを追加します。ラベルと色を選び、チャート上の価格をクリックすると水平ラインが追加されます。`完了してデイトレードへ` を押すと、追加した水平ラインを表示したまま分足の練習画面へ進みます。

サイドバーで以下を変更できます。

- 銘柄コード
- 日付
- 実データ / サンプル
- 再生速度
- 再生 / 一時停止
- 分足チャートの足種と表示範囲
- 日足 / 週足 / 月足チャート
- 指標表示
- 口座入金額
- 注文株数

## CLIバックテスト

単日:

```bash
python run_backtest.py --symbol 285A --date 2026-06-24 --strategy vwap_ma_breakout
```

サンプルデータで実行する場合:

```bash
python run_backtest.py --symbol 285A --date 2026-06-24 --strategy vwap_ma_breakout --data-source sample
```

複数日:

```bash
python run_backtest.py --symbol 285A --start 2026-06-01 --end 2026-06-30 --strategy vwap_ma_breakout
```

利用できる戦略:

- `vwap_ma_breakout`
- `bollinger_reversion`
- `combined_rule`

出力先:

```text
outputs/
  reports/
  trades/
  equity/
```

## テスト

```bash
pytest
```

## データ形式

1分足CSV:

```csv
timestamp,open,high,low,close,volume
2026-06-24 09:00:00,90000,91080,89280,90540,120000
```

日足CSV:

```csv
date,open,high,low,close,volume
2026-06-24,90000,91800,88200,90750,18000000
```

## 設計メモ

手動UIも自動売買戦略も、同じ `TradingEnvironment` に `Action` を送ります。戦略はBrokerを直接知らず、観測データだけを見て `BUY` / `SELL` / `CLOSE` / `HOLD` を返します。

練習日より後の日足は読み込まず、練習中の当日日足は再生済み1分足から動的に作ります。

詳細仕様と再作成手順は [docs/APP_SPEC.md](docs/APP_SPEC.md) にまとめています。

## 注意

本アプリは過去の株価データを用いたトレード練習・シミュレーション用アプリです。実際の投資判断を推奨するものではありません。表示される価格・損益はシミュレーションであり、実際の約定価格や取引結果を保証するものではありません。
