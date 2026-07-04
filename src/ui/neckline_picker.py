from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit.components.v1 as components

from src.ui.chart import long_term_chart_frame


NECKLINE_LABELS = [
    "サポートライン",
    "レジスタンスライン",
    "直近高値",
    "直近安値",
    "移動平均線",
    "ボリンジャーバンド",
    "その他",
]

NECKLINE_COLORS = {
    "紫": "#7c3aed",
    "緑": "#059669",
    "赤": "#dc2626",
    "青": "#2563eb",
    "橙": "#ea580c",
}

_COMPONENT_PATH = Path(__file__).parent / "components" / "neckline_picker"
_neckline_picker = components.declare_component("neckline_picker", path=str(_COMPONENT_PATH))


def render_neckline_picker(
    obs: dict,
    show: dict[str, bool],
    necklines: list[dict],
    *,
    label: str,
    color: str,
    key: str = "neckline_picker",
) -> dict | None:
    daily = long_term_chart_frame(obs["daily_bars"], "日足")
    records = _records_for_component(daily)
    return _neckline_picker(
        records=records,
        show={"daily_ma": bool(show.get("daily_ma")), "bollinger": bool(show.get("bollinger"))},
        necklines=necklines,
        label=label,
        color=color,
        default=None,
        key=key,
    )


def _records_for_component(frame: pd.DataFrame) -> list[dict]:
    columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ma_5",
        "ma_25",
        "ma_75",
        "bb_upper_1",
        "bb_lower_1",
        "bb_upper_2",
        "bb_lower_2",
        "bb_upper_3",
        "bb_lower_3",
    ]
    available = [column for column in columns if column in frame.columns]
    result = frame[available].copy()
    result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
    result = result.astype(object).where(pd.notna(result), None)
    return result.to_dict("records")
