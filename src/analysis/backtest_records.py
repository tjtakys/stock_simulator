from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import ROOT_DIR
from src.strategies.daytrade_modes import DAYTRADE_MODE_LABELS


RECORD_PATH = ROOT_DIR / "docs" / "REAL_DATA_BACKTESTS.md"
README_PATH = ROOT_DIR / "README.md"

RECORD_START = "<!-- REAL_DATA_BACKTEST_RECORDS_START -->"
RECORD_END = "<!-- REAL_DATA_BACKTEST_RECORDS_END -->"
README_START = "<!-- REAL_DATA_RESULTS_START -->"
README_END = "<!-- REAL_DATA_RESULTS_END -->"

RECORD_COLUMNS = [
    "recorded_on",
    "symbol",
    "symbol_name",
    "trading_date",
    "day_note",
    "previous_change",
    "strategy",
    "quantity",
    "total_pnl",
    "win_rate",
    "trade_count",
    "chart",
    "report",
    "include_in_readme",
    "memo",
]

RECORD_HEADERS = [
    "記録日",
    "銘柄コード",
    "銘柄名",
    "検証日",
    "当日の特徴",
    "前日比",
    "戦略",
    "株数",
    "損益",
    "勝率",
    "取引数",
    "チャート",
    "レポート",
    "README掲載",
    "メモ",
]

README_HEADERS = ["銘柄", "日付", "当日の特徴", "前日比", "戦略", "損益", "勝率", "取引数", "チャート", "メモ"]

STRATEGY_LABELS = {
    **DAYTRADE_MODE_LABELS,
    "bollinger_next_reversion": "ボリンジャー3σ逆張り",
    "vwap_ma_breakout": "VWAP + 移動平均ブレイクアウト",
    "bollinger_reversion": "ボリンジャー逆張り",
    "combined_rule": "複合ルール",
}


@dataclass(frozen=True)
class BacktestRecord:
    recorded_on: str
    symbol: str
    symbol_name: str
    trading_date: str
    day_note: str
    previous_change: str
    strategy: str
    quantity: str
    total_pnl: str
    win_rate: str
    trade_count: str
    chart: str
    report: str
    include_in_readme: str
    memo: str

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.symbol, self.trading_date, self.strategy, self.quantity)


def build_backtest_record(
    *,
    symbol: str,
    symbol_name: str,
    trading_date: date,
    strategy_name: str,
    quantity: int,
    metrics: dict,
    minute: pd.DataFrame,
    daily: pd.DataFrame,
    report_path: Path,
    chart_path: Path | None = None,
    memo: str = "",
    include_in_readme: bool = False,
    recorded_on: date | None = None,
) -> BacktestRecord:
    return BacktestRecord(
        recorded_on=(recorded_on or date.today()).isoformat(),
        symbol=symbol.upper(),
        symbol_name=symbol_name,
        trading_date=trading_date.isoformat(),
        day_note=describe_intraday(minute),
        previous_change=describe_previous_change(minute, daily, trading_date),
        strategy=strategy_label(strategy_name),
        quantity=f"{quantity:,}",
        total_pnl=format_yen(metrics.get("total_pnl", 0.0)),
        win_rate=format_percent(metrics.get("win_rate", 0.0)),
        trade_count=str(int(metrics.get("trade_count", 0))),
        chart=markdown_link("チャート", chart_path, RECORD_PATH.parent) if chart_path is not None else "",
        report=markdown_link("HTML", report_path, RECORD_PATH.parent),
        include_in_readme="yes" if include_in_readme else "no",
        memo=memo,
    )


def record_backtest_result(
    record: BacktestRecord,
    *,
    record_path: Path = RECORD_PATH,
    readme_path: Path = README_PATH,
) -> None:
    records = read_records(record_path)
    records_by_key = {item.key: item for item in records}
    records_by_key[record.key] = record
    updated = sorted(records_by_key.values(), key=lambda item: (item.trading_date, item.symbol, item.strategy))
    write_records(updated, record_path)
    update_readme_results(updated, readme_path)


def read_records(path: Path = RECORD_PATH) -> list[BacktestRecord]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    body = _between_markers(text, RECORD_START, RECORD_END)
    if body is None:
        return []

    records: list[BacktestRecord] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = _split_table_row(line)
        if cells == RECORD_HEADERS or _is_separator(cells) or cells[0] == "記録日":
            continue
        if len(cells) != len(RECORD_COLUMNS):
            cells = _upgrade_legacy_cells(cells)
            if len(cells) != len(RECORD_COLUMNS):
                continue
        if not any(cells):
            continue
        values = dict(zip(RECORD_COLUMNS, cells, strict=True))
        records.append(BacktestRecord(**values))
    return records


def write_records(records: Iterable[BacktestRecord], path: Path = RECORD_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _render_table(RECORD_HEADERS, ([asdict(record)[column] for column in RECORD_COLUMNS] for record in records))
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = _initial_record_document()
    path.write_text(_replace_between_markers(text, RECORD_START, RECORD_END, body), encoding="utf-8")


def update_readme_results(records: Iterable[BacktestRecord], path: Path = README_PATH) -> None:
    records_for_readme = [record for record in records if record.include_in_readme.lower() == "yes"]
    body = _render_table(README_HEADERS, (_readme_row(record) for record in records_for_readme))
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = f"## 実データ検証成績\n\n{README_START}\n{README_END}\n"
    path.write_text(_replace_between_markers(text, README_START, README_END, body), encoding="utf-8")


def describe_intraday(minute: pd.DataFrame) -> str:
    if minute.empty:
        return "-"
    first = minute.iloc[0]
    last = minute.iloc[-1]
    open_price = float(first["open"])
    close_price = float(last["close"])
    high = float(minute["high"].max())
    low = float(minute["low"].min())
    if open_price <= 0:
        return "-"

    day_change = (close_price - open_price) / open_price
    range_pct = (high - low) / open_price
    direction = "上昇" if day_change > 0 else "下落" if day_change < 0 else "横ばい"
    return f"{direction} / 日中値幅 {range_pct * 100:.2f}%"


def describe_previous_change(minute: pd.DataFrame, daily: pd.DataFrame, trading_date: date) -> str:
    if minute.empty or daily.empty:
        return "-"
    previous = daily[pd.to_datetime(daily["date"]).dt.date < trading_date]
    if previous.empty:
        return "-"
    previous_close = float(previous.iloc[-1]["close"])
    close_price = float(minute.iloc[-1]["close"])
    if previous_close <= 0:
        return "-"
    change = close_price - previous_close
    return f"{change:+,.1f}円 ({change / previous_close * 100:+.2f}%)"


def strategy_label(strategy_name: str) -> str:
    return STRATEGY_LABELS.get(strategy_name, strategy_name)


def format_yen(value: object) -> str:
    amount = float(value)
    return f"{amount:+,.0f}円"


def format_percent(value: object) -> str:
    return f"{float(value) * 100:.1f}%"


def markdown_link(label: str, target: Path, base_dir: Path) -> str:
    relative = os.path.relpath(target, base_dir)
    return f"[{_escape_cell(label)}]({_escape_cell(relative)})"


def _readme_row(record: BacktestRecord) -> list[str]:
    symbol = f"{record.symbol} {record.symbol_name}".strip()
    return [
        symbol,
        record.trading_date,
        record.day_note,
        record.previous_change,
        record.strategy,
        record.total_pnl,
        record.win_rate,
        record.trade_count,
        _readme_link(record.chart),
        record.memo,
    ]


def _render_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    rendered_rows = [_table_row(headers), _table_row(["---"] * len(headers))]
    rendered_rows.extend(_table_row(row) for row in rows)
    if len(rendered_rows) == 2:
        rendered_rows.append(_table_row([""] * len(headers)))
    return "\n".join(rendered_rows)


def _table_row(values: list[str]) -> str:
    return "| " + " | ".join(_escape_cell(value) for value in values) + " |"


def _escape_cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", "/").strip()


def _readme_link(value: str) -> str:
    return value.replace("](../outputs/", "](outputs/").replace("](assets/", "](docs/assets/")


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(set(cell) <= {"-", ":", " "} and "-" in cell for cell in cells)


def _upgrade_legacy_cells(cells: list[str]) -> list[str]:
    legacy_columns = [column for column in RECORD_COLUMNS if column != "chart"]
    if len(cells) == len(legacy_columns):
        chart_index = RECORD_COLUMNS.index("chart")
        return [*cells[:chart_index], "", *cells[chart_index:]]
    return cells


def _between_markers(text: str, start: str, end: str) -> str | None:
    start_index = text.find(start)
    end_index = text.find(end)
    if start_index < 0 or end_index < 0 or end_index < start_index:
        return None
    return text[start_index + len(start) : end_index]


def _replace_between_markers(text: str, start: str, end: str, body: str) -> str:
    start_index = text.find(start)
    end_index = text.find(end)
    if start_index < 0 or end_index < 0 or end_index < start_index:
        raise ValueError(f"更新用マーカーが見つかりません: {start} / {end}")
    return f"{text[: start_index + len(start)]}\n{body}\n{text[end_index:]}"


def _initial_record_document() -> str:
    return f"""# 実データ検証記録

実データを使ったバックテストの記録です。READMEには `README掲載` が `yes` の結果だけを抜粋します。

{RECORD_START}
{RECORD_END}
"""
