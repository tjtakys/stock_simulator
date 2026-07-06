from __future__ import annotations

from datetime import date

from src.ui import sidebar


class _FakeSidebar:
    def __init__(self) -> None:
        self.selectboxes: dict[str, list[str]] = {}

    def header(self, *args, **kwargs) -> None:
        pass

    def subheader(self, *args, **kwargs) -> None:
        pass

    def text_input(self, *args, **kwargs) -> str:
        return "285A"

    def date_input(self, *args, **kwargs) -> date:
        return date(2026, 6, 24)

    def radio(self, label, options, **kwargs):
        return options[0]

    def button(self, *args, **kwargs) -> bool:
        return False

    def selectbox(self, label, options, **kwargs):
        self.selectboxes[label] = list(options)
        return options[0]

    def toggle(self, *args, **kwargs) -> bool:
        return bool(kwargs.get("value", False))

    def checkbox(self, *args, **kwargs) -> bool:
        return bool(kwargs.get("value", False))

    def number_input(self, *args, **kwargs):
        return kwargs["value"]


class _FakeStreamlit:
    def __init__(self) -> None:
        self.sidebar = _FakeSidebar()


def test_sidebar_exposes_all_implemented_auto_strategies(monkeypatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(sidebar, "st", fake_st)

    sidebar.render_sidebar()

    assert fake_st.sidebar.selectboxes["売買アルゴリズム"] == [
        "bollinger_next_reversion",
        "vwap_ma_breakout",
        "bollinger_reversion",
        "combined_rule",
    ]
