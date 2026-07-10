# デイトレード練習・自動売買検証シミュレーター

ブラウザ上で動作する、デイトレード練習とルールベース売買戦略検証のためのローカルアプリです。OpenAI Codex を使って作成しています。

<video src="docs/assets/demo_movie.mov" controls width="960"></video>

[デモ動画を開く](https://github.com/user-attachments/assets/8d6db9ef-b70e-456d-a1af-a27ec49e3a4a)


## 使い方

```bash
conda env create -f environment.yml
conda activate sim
streamlit run app.py
```

ブラウザで `http://127.0.0.1:8501` を開きます。

## トラブルシュート

コード更新後に、最新版のはずなのに古い関数定義を参照するエラーが出る場合は、Streamlit の古いプロセスが残っている可能性があります。

```bash
pkill -f streamlit
conda activate sim
streamlit run app.py
```

## 詳細

機能、仕様、データ形式、再作成手順は [docs/APP_SPEC.md](docs/APP_SPEC.md) にまとめています。
デイトレード手法モードの詳細は [docs/daytrade_strategy_modes_spec_ja.md](docs/daytrade_strategy_modes_spec_ja.md) に分けて管理しています。

## 売買戦略

- 押し目重視手法、標準デイトレ手法、積極ブレイク手法
- 15分足、30分足、60分足のボリンジャーバンド ±3σ での逆張り
- VWAP反発、直近高値ブレイク、前日高値ブレイク、出来高急増ブレイク
- VWAP と移動平均線を超えた場合の順張り
- 空売りと買い戻し
- 日足の重要価格ラインを上抜けた場合の買い
- 日足のレジスタンスライン接近時の余裕を持った売り
- 日足ボリンジャーバンド +3σ / -3σ 到達時の逆張り・利確
- 一定以上の損失が出た場合のロスカット

## 実データ検証成績

全記録は [docs/REAL_DATA_BACKTESTS.md](docs/REAL_DATA_BACKTESTS.md) に保存します。READMEには代表的な結果だけを抜粋します。

<!-- REAL_DATA_RESULTS_START -->
| 銘柄 | 日付 | 当日の特徴 | 前日比 | 戦略 | 損益 | 勝率 | 取引数 | チャート | メモ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 285A キオクシアホールディングス | 2026-07-10 | 下落 / 日中値幅 9.95% | -1,610.0円 (-2.07%) | 標準デイトレ手法 | -68,000円 | 40.0% | 5 | [チャート](docs/assets/backtests/285A_2026-07-10_combined_normal_chart.png) | 7/10のキオクシアホールディングスを更新後の標準デイトレ手法で検証 |
| 6976 太陽誘電 | 2026-07-10 | 下落 / 日中値幅 7.49% | -70.0円 (-0.48%) | 標準デイトレ手法 | -1,000円 | 25.0% | 4 | [チャート](docs/assets/backtests/6976_2026-07-10_combined_normal_chart.png) | 7/10の太陽誘電を更新後の標準デイトレ手法で検証 |
| 6981 村田製作所 | 2026-07-10 | 上昇 / 日中値幅 4.52% | +275.0円 (+2.90%) | 標準デイトレ手法 | -4,700円 | 36.4% | 11 | [チャート](docs/assets/backtests/6981_2026-07-10_combined_normal_chart.png) | 7/10の村田製作所を更新後の標準デイトレ手法で検証 |
| 8035 東京エレクトロン | 2026-07-10 | 上昇 / 日中値幅 4.07% | +1,500.0円 (+2.11%) | 標準デイトレ手法 | +158,000円 | 40.0% | 15 | [チャート](docs/assets/backtests/8035_2026-07-10_combined_normal_chart.png) | 7/10の東京エレクトロンを更新後の標準デイトレ手法で検証 |
<!-- REAL_DATA_RESULTS_END -->

## 注意

本アプリは過去データを使った練習・検証用です。実売買APIには接続せず、実際の投資判断を推奨するものではありません。
