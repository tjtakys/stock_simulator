from __future__ import annotations

import streamlit as st

from src.simulator.order import Action


def render_action_buttons(is_playing: bool = False) -> Action | str | None:
    buy_col, sell_col, close_col, back_col, step_col, play_col, reset_col, run_col = st.columns(8)
    buy_clicked = buy_col.button("買い", width="stretch")
    sell_clicked = sell_col.button("空売り", width="stretch")
    close_clicked = close_col.button("決済", width="stretch")
    back_clicked = back_col.button("1分戻る", width="stretch")
    step_clicked = step_col.button("1分進める", width="stretch")
    play_clicked = play_col.button("一時停止" if is_playing else "再生", width="stretch")
    reset_clicked = reset_col.button("リセット", width="stretch")
    run_clicked = run_col.button("最後まで", width="stretch")

    if buy_clicked:
        return Action.BUY
    if sell_clicked:
        return Action.SELL
    if close_clicked:
        return Action.CLOSE
    if back_clicked:
        return "STEP_BACK"
    if step_clicked:
        return Action.HOLD
    if play_clicked:
        return "PAUSE" if is_playing else "PLAY"
    if reset_clicked:
        return "RESET_REPLAY"
    if run_clicked:
        return "RUN_TO_END"
    return None
