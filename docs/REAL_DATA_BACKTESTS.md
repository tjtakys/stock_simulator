# 実データ検証記録

実データを使ったバックテストの記録です。READMEには `README掲載` が `yes` の結果だけを抜粋します。

```bash
conda run -n sim python scripts/record_real_data_backtest.py --symbol 6976 --date 2026-07-10 --include-readme
```

<!-- REAL_DATA_BACKTEST_RECORDS_START -->
| 記録日 | 銘柄コード | 銘柄名 | 検証日 | 当日の特徴 | 前日比 | 戦略 | 株数 | 損益 | 勝率 | 取引数 | チャート | レポート | README掲載 | メモ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-07-11 | 285A | キオクシアホールディングス | 2026-07-10 | 下落 / 日中値幅 9.95% | -1,610.0円 (-2.07%) | 標準デイトレ手法 | 100 | -68,000円 | 40.0% | 5 | [チャート](assets/backtests/285A_2026-07-10_combined_normal_chart.png) | [HTML](../outputs/reports/285A_2026-07-10_combined_normal.html) | yes | 7/10のキオクシアホールディングスを更新後の標準デイトレ手法で検証 |
| 2026-07-11 | 6976 | 太陽誘電 | 2026-07-10 | 下落 / 日中値幅 7.49% | -70.0円 (-0.48%) | 標準デイトレ手法 | 100 | -1,000円 | 25.0% | 4 | [チャート](assets/backtests/6976_2026-07-10_combined_normal_chart.png) | [HTML](../outputs/reports/6976_2026-07-10_combined_normal.html) | yes | 7/10の太陽誘電を更新後の標準デイトレ手法で検証 |
| 2026-07-11 | 6981 | 村田製作所 | 2026-07-10 | 上昇 / 日中値幅 4.52% | +275.0円 (+2.90%) | 標準デイトレ手法 | 100 | -4,700円 | 36.4% | 11 | [チャート](assets/backtests/6981_2026-07-10_combined_normal_chart.png) | [HTML](../outputs/reports/6981_2026-07-10_combined_normal.html) | yes | 7/10の村田製作所を更新後の標準デイトレ手法で検証 |
| 2026-07-11 | 8035 | 東京エレクトロン | 2026-07-10 | 上昇 / 日中値幅 4.07% | +1,500.0円 (+2.11%) | 標準デイトレ手法 | 100 | +158,000円 | 40.0% | 15 | [チャート](assets/backtests/8035_2026-07-10_combined_normal_chart.png) | [HTML](../outputs/reports/8035_2026-07-10_combined_normal.html) | yes | 7/10の東京エレクトロンを更新後の標準デイトレ手法で検証 |
<!-- REAL_DATA_BACKTEST_RECORDS_END -->
