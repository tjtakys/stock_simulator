from __future__ import annotations

import streamlit as st

from src.simulator.order import Action


def render_action_buttons(is_playing: bool = False) -> Action | str | None:
    buy_col, sell_col, close_col, step_col, play_col, run_col = st.columns(6)
    if buy_col.button("買い", width="stretch"):
        return Action.BUY
    if sell_col.button("空売り", width="stretch"):
        return Action.SELL
    if close_col.button("決済", width="stretch"):
        return Action.CLOSE
    if step_col.button("1分進める", width="stretch"):
        return Action.HOLD
    if play_col.button("一時停止" if is_playing else "再生", width="stretch"):
        return "PAUSE" if is_playing else "PLAY"
    if run_col.button("最後まで", width="stretch"):
        return "RUN_TO_END"
    return None
