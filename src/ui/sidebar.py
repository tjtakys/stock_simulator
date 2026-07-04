from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.config import DEFAULT_DATE, DEFAULT_INITIAL_CASH, DEFAULT_ORDER_QUANTITY, DEFAULT_SYMBOL


def render_sidebar() -> dict:
    st.sidebar.header("設定")
    symbol = st.sidebar.text_input("銘柄コード", value=DEFAULT_SYMBOL).strip().upper() or DEFAULT_SYMBOL
    trading_date = st.sidebar.date_input("日付", value=datetime.strptime(DEFAULT_DATE, "%Y-%m-%d").date())
    data_source_label = st.sidebar.radio("データ", ["実データ（Yahooファイナンス）", "サンプル"], index=0)
    refresh_data = st.sidebar.button("実データを再取得", width="stretch")
    speed_labels = {
        "step": "手動",
        "1x": "標準",
        "10x": "10倍速",
        "30x": "30倍速",
        "60x": "60倍速",
    }
    speed = st.sidebar.selectbox(
        "再生速度",
        list(speed_labels),
        index=4,
        format_func=lambda value: speed_labels[value],
    )
    display_window = st.sidebar.selectbox("表示範囲", ["過去10分", "過去30分", "過去60分", "全表示"], index=1)
    chart_type = st.sidebar.radio(
        "チャート",
        ["1分足", "3分足", "5分足", "10分足", "30分足", "60分足", "日足", "週足", "月足"],
        horizontal=True,
    )

    st.sidebar.subheader("指標")
    show_vwap = st.sidebar.checkbox("出来高加重平均価格", value=True)
    show_minute_ma = st.sidebar.checkbox("分足の移動平均線", value=True)
    show_daily_ma = st.sidebar.checkbox("長期足の移動平均線", value=True)
    show_bollinger = st.sidebar.checkbox("ボリンジャーバンド", value=True)

    initial_cash = st.sidebar.number_input(
        "口座入金額",
        min_value=100_000,
        max_value=1_000_000_000,
        value=int(DEFAULT_INITIAL_CASH),
        step=1_000_000,
    )
    quantity = st.sidebar.number_input("注文株数", min_value=1, max_value=100_000, value=DEFAULT_ORDER_QUANTITY, step=100)
    reset = st.sidebar.button("リセット", width="stretch")
    return {
        "symbol": symbol,
        "trading_date": trading_date,
        "data_source": "yahoo" if data_source_label.startswith("実データ") else "sample",
        "data_source_label": data_source_label,
        "refresh_data": refresh_data,
        "speed": speed,
        "display_window": display_window,
        "chart_type": chart_type,
        "initial_cash": float(initial_cash),
        "quantity": int(quantity),
        "reset": reset,
        "show": {
            "vwap": show_vwap,
            "minute_ma": show_minute_ma,
            "daily_ma": show_daily_ma,
            "bollinger": show_bollinger,
        },
    }
