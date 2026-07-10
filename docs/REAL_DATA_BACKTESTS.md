# 実データ検証記録

実データを使ったバックテストの記録です。READMEには `README掲載` が `yes` の結果だけを抜粋します。

```bash
conda run -n sim python scripts/record_real_data_backtest.py --symbol 6976 --date 2026-07-10 --include-readme
```

<!-- REAL_DATA_BACKTEST_RECORDS_START -->
| 記録日 | 銘柄コード | 銘柄名 | 検証日 | 当日の特徴 | 前日比 | 戦略 | 株数 | 損益 | 勝率 | 取引数 | チャート | レポート | README掲載 | メモ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-07-11 | 6976 | 太陽誘電 | 2026-07-10 | 下落 / 日中値幅 7.49% | -70.0円 (-0.48%) | 標準デイトレ手法 | 100 | -1,000円 | 25.0% | 4 | [チャート](assets/backtests/6976_2026-07-10_combined_normal_chart.png) | [HTML](../outputs/reports/6976_2026-07-10_combined_normal.html) | yes | 7/10の太陽誘電を更新後の標準デイトレ手法で検証 |
<!-- REAL_DATA_BACKTEST_RECORDS_END -->
