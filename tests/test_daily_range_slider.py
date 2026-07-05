from __future__ import annotations

import pandas as pd

import app


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.select_slider_call: dict[str, object] | None = None
        self.caption_text: str | None = None

    def select_slider(self, label, **kwargs):
        kwargs["label"] = label
        self.select_slider_call = kwargs
        options = kwargs["options"]
        return (options[1], options[3])

    def button(self, *args, **kwargs) -> bool:
        return False

    def caption(self, text: str) -> None:
        self.caption_text = text


def test_daily_range_slider_uses_date_options(monkeypatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(app, "st", fake_st)
    daily = pd.DataFrame(
        {
            "date": pd.date_range("2026-06-01", periods=5, freq="B"),
            "open": range(100, 105),
            "high": range(101, 106),
            "low": range(99, 104),
            "close": range(100, 105),
            "volume": [1000] * 5,
        }
    )
    obs = {"symbol": "285A", "date": pd.Timestamp("2026-06-08").date(), "daily_bars": daily}

    selected_range = app._render_daily_range_slider(obs)

    assert selected_range == (1, 3)
    assert fake_st.select_slider_call is not None
    assert fake_st.select_slider_call["label"] == "日足表示範囲"
    assert fake_st.select_slider_call["value"] == (
        pd.Timestamp("2026-06-01").date(),
        pd.Timestamp("2026-06-05").date(),
    )
    assert fake_st.select_slider_call["format_func"](pd.Timestamp("2026-06-02").date()) == "2026-06-02"
    assert fake_st.caption_text == "選択範囲: 2026-06-02 〜 2026-06-04"
