from __future__ import annotations

from dataclasses import replace

from src.analysis.backtest_records import (
    README_END,
    README_START,
    RECORD_END,
    RECORD_START,
    BacktestRecord,
    read_records,
    record_backtest_result,
)


def test_record_backtest_result_updates_record_file_and_readme(tmp_path):
    record_path = tmp_path / "REAL_DATA_BACKTESTS.md"
    readme_path = tmp_path / "README.md"
    record_path.write_text(f"# Log\n\n{RECORD_START}\n{RECORD_END}\n", encoding="utf-8")
    readme_path.write_text(f"# App\n\n## 実データ検証成績\n\n{README_START}\n{README_END}\n", encoding="utf-8")

    record = BacktestRecord(
        recorded_on="2026-07-10",
        symbol="6976",
        symbol_name="太陽誘電",
        trading_date="2026-07-10",
        day_note="上昇 / 日中値幅 2.50%",
        previous_change="+10.0円 (+0.50%)",
        strategy="標準デイトレ手法",
        quantity="100",
        total_pnl="+1,000円",
        win_rate="50.0%",
        trade_count="2",
        chart="[チャート](assets/backtests/6976_2026-07-10_combined_normal_chart.png)",
        report="[HTML](../outputs/reports/6976_2026-07-10_combined_normal.html)",
        include_in_readme="yes",
        memo="記録テスト",
    )

    record_backtest_result(record, record_path=record_path, readme_path=readme_path)

    record_text = record_path.read_text(encoding="utf-8")
    readme_text = readme_path.read_text(encoding="utf-8")
    assert "| 2026-07-10 | 6976 | 太陽誘電 |" in record_text
    assert "| 6976 太陽誘電 | 2026-07-10 |" in readme_text
    assert "[チャート](docs/assets/backtests/6976_2026-07-10_combined_normal_chart.png)" in readme_text
    assert "記録テスト" in readme_text

    updated = replace(record, total_pnl="+2,000円", trade_count="3")
    record_backtest_result(updated, record_path=record_path, readme_path=readme_path)

    record_text = record_path.read_text(encoding="utf-8")
    assert record_text.count("| 2026-07-10 | 6976 | 太陽誘電 |") == 1
    assert "+2,000円" in record_text


def test_record_backtest_result_omits_non_representative_records_from_readme(tmp_path):
    record_path = tmp_path / "REAL_DATA_BACKTESTS.md"
    readme_path = tmp_path / "README.md"
    record_path.write_text(f"# Log\n\n{RECORD_START}\n{RECORD_END}\n", encoding="utf-8")
    readme_path.write_text(f"# App\n\n{README_START}\n{README_END}\n", encoding="utf-8")
    record = BacktestRecord(
        recorded_on="2026-07-10",
        symbol="6976",
        symbol_name="太陽誘電",
        trading_date="2026-07-10",
        day_note="横ばい / 日中値幅 0.50%",
        previous_change="-",
        strategy="標準デイトレ手法",
        quantity="100",
        total_pnl="+0円",
        win_rate="0.0%",
        trade_count="0",
        chart="[チャート](assets/backtests/example.html)",
        report="[HTML](../outputs/reports/example.html)",
        include_in_readme="no",
        memo="READMEには載せない",
    )

    record_backtest_result(record, record_path=record_path, readme_path=readme_path)

    readme_text = readme_path.read_text(encoding="utf-8")
    assert "READMEには載せない" not in readme_text
    assert "|  |  |  |  |  |  |  |  |  |  |" in readme_text


def test_read_records_skips_legacy_header_rows(tmp_path):
    record_path = tmp_path / "REAL_DATA_BACKTESTS.md"
    record_path.write_text(
        f"""# Log

{RECORD_START}
| 記録日 | 銘柄コード | 銘柄名 | 検証日 | 当日の特徴 | 前日比 | 戦略 | 株数 | 損益 | 勝率 | 取引数 | レポート | README掲載 | メモ |
| 2026-07-11 | 6976 | 太陽誘電 | 2026-07-10 | 下落 | - | 積極ブレイク手法 | 100 | +0円 | 0.0% | 0 | [HTML](../outputs/reports/example.html) | yes | test |
{RECORD_END}
""",
        encoding="utf-8",
    )

    records = read_records(record_path)

    assert len(records) == 1
    assert records[0].symbol == "6976"
    assert records[0].chart == ""
