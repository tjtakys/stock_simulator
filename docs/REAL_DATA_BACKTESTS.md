# 実データ検証記録

実データを使ったバックテストの記録です。READMEには `README掲載` が `yes` の結果だけを抜粋します。

```bash
conda run -n sim python scripts/record_real_data_backtest.py --symbol 6976 --date 2026-07-10 --include-readme
```

<!-- REAL_DATA_BACKTEST_RECORDS_START -->
| 記録日 | 銘柄コード | 銘柄名 | 検証日 | 当日の特徴 | 前日比 | 戦略 | 株数 | 損益 | 勝率 | 取引数 | チャート | レポート | README掲載 | メモ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-07-10 | 6976 | 太陽誘電 | 2026-07-10 | 下落 / 日中値幅 7.49% | -70.0円 (-0.48%) | 標準デイトレ手法 | 100 | +0円 | 0.0% | 0 |  | [HTML](../outputs/reports/6976_2026-07-10_combined_normal.html) | yes | 今日の太陽誘電を標準デイトレ手法で検証 |
| 2026-07-11 | 6976 | 太陽誘電 | 2026-07-10 | 下落 / 日中値幅 7.49% | -70.0円 (-0.48%) | 積極ブレイク手法 | 100 | +0円 | 0.0% | 0 | [チャート](assets/backtests/6976_2026-07-10_combined_high_risk_chart.html) | [HTML](../outputs/reports/6976_2026-07-10_combined_high_risk.html) | yes | 7/10の太陽誘電をハイリスク手法で検証 |
<!-- REAL_DATA_BACKTEST_RECORDS_END -->
