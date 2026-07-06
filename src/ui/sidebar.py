from __future__ import annotations

import streamlit as st

from src.config import DEFAULT_INITIAL_CASH, DEFAULT_ORDER_QUANTITY, DEFAULT_SYMBOL, default_trading_date


def render_sidebar() -> dict:
    st.sidebar.header("設定")
    symbol = st.sidebar.text_input("銘柄コード", value=DEFAULT_SYMBOL).strip().upper() or DEFAULT_SYMBOL
    trading_date = st.sidebar.date_input("日付", value=default_trading_date())
    data_source_label = st.sidebar.radio("データ", ["実データ（Yahooファイナンス）", "サンプル"], index=0)
    refresh_data = st.sidebar.button("実データを再取得", width="stretch")
    speed_labels = {
        "step": "手動",
        "1x": "標準",
        "10x": "10倍速",
        "30x": "30倍速",
        "60x": "60倍速",
        "120x": "120倍速",
        "240x": "240倍速",
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
    use_necklines = st.sidebar.toggle(
        "重要価格ラインを使う",
        value=True,
        help="OFFにすると日足での重要価格ライン設定を省略し、日付変更時も設定画面へ戻りません。",
    )

    st.sidebar.subheader("指標")
    show_vwap = st.sidebar.checkbox("出来高加重平均価格", value=True)
    show_minute_ma = st.sidebar.checkbox("分足の移動平均線", value=True)
    show_daily_ma = st.sidebar.checkbox("長期足の移動平均線", value=True)
    show_bollinger = st.sidebar.checkbox("ボリンジャーバンド", value=True)

    st.sidebar.subheader("自動売買")
    auto_trade = st.sidebar.checkbox("自動売買モード", value=False)
    strategy_labels = {
        "bollinger_next_reversion": "ボリンジャー3σ逆張り",
        "vwap_ma_breakout": "VWAP + 移動平均ブレイクアウト",
        "bollinger_reversion": "ボリンジャー逆張り",
        "combined_rule": "複合ルール",
    }
    auto_strategy = st.sidebar.selectbox(
        "売買アルゴリズム",
        list(strategy_labels),
        format_func=lambda value: strategy_labels[value],
        disabled=not auto_trade,
    )
    batch_mode = st.sidebar.checkbox(
        "一括検証モード",
        value=False,
        disabled=not auto_trade,
        help="再生ボタンで、選択中の自動売買アルゴリズムを当日の最後まで即時実行します。",
    )
    batch_run = st.sidebar.button(
        "一括検証を実行",
        width="stretch",
        disabled=not auto_trade,
        help="倍速再生を待たずに、選択中の自動売買アルゴリズムを当日の最後まで実行します。",
    )

    initial_cash = st.sidebar.number_input(
        "口座入金額",
        min_value=100_000,
        max_value=1_000_000_000,
        value=int(DEFAULT_INITIAL_CASH),
        step=1_000_000,
    )
    quantity = st.sidebar.number_input("注文株数", min_value=1, max_value=100_000, value=DEFAULT_ORDER_QUANTITY, step=100)
    reset = st.sidebar.button(
        "ライン設定からやり直す",
        width="stretch",
        disabled=not use_necklines,
    )
    return {
        "symbol": symbol,
        "trading_date": trading_date,
        "data_source": "yahoo" if data_source_label.startswith("実データ") else "sample",
        "data_source_label": data_source_label,
        "refresh_data": refresh_data,
        "speed": speed,
        "display_window": display_window,
        "chart_type": chart_type,
        "use_necklines": bool(use_necklines),
        "auto_trade": bool(auto_trade),
        "auto_strategy": auto_strategy,
        "batch_mode": bool(auto_trade and batch_mode),
        "batch_run": bool(auto_trade and batch_run),
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
