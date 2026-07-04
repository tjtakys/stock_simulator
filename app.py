from __future__ import annotations

from html import escape
import time

import pandas as pd
import streamlit as st

from src.config import ensure_project_dirs, symbol_display_name
from src.data.providers.yahoo import RealDataUnavailable, yahoo_symbol
from src.simulator.environment import TradingEnvironment
from src.simulator.order import Action
from src.simulator.position import PositionSide
from src.ui.chart import daily_chart, minute_chart
from src.ui.controls import render_action_buttons
from src.ui.neckline_picker import NECKLINE_COLORS, NECKLINE_LABELS, render_neckline_picker
from src.ui.sidebar import render_sidebar


st.set_page_config(page_title="デイトレードシミュレーター", layout="wide")


def _env_key(inputs: dict) -> tuple:
    return (inputs["symbol"], inputs["trading_date"].isoformat(), inputs["data_source"], inputs["initial_cash"])


def _speed_interval_seconds(speed: str) -> float | None:
    return {
        "step": None,
        "1x": 60.0,
        "10x": 6.0,
        "30x": 2.0,
        "60x": 1.0,
    }[speed]


def _sync_neckline_context(key: tuple, reset: bool = False) -> None:
    if reset or st.session_state.get("neckline_context") != key:
        st.session_state.neckline_context = key
        st.session_state.necklines = []
        st.session_state.neckline_setup_done = False
        st.session_state.last_neckline_nonce = None


def _render_neckline_setup(obs: dict, show: dict[str, bool]) -> None:
    st.subheader("日足でネックラインを設定")
    st.info("デイトレードを始める前に、日足チャート上で意識したい価格をクリックして水平ラインを追加してください。")

    necklines = st.session_state.setdefault("necklines", [])

    st.plotly_chart(
        daily_chart(obs, show, "日足", necklines),
        width="stretch",
        key="neckline_reference_daily_chart",
    )

    label_col, custom_col, color_col = st.columns([1.1, 1.3, 0.7])
    selected_label = label_col.selectbox("ラベル", NECKLINE_LABELS, index=0)
    custom_label = custom_col.text_input("ラベル名", value="", disabled=selected_label != "その他")
    label = custom_label.strip() if selected_label == "その他" and custom_label.strip() else selected_label
    color_name = color_col.selectbox("色", list(NECKLINE_COLORS), index=0)
    color = NECKLINE_COLORS[color_name]

    picked = render_neckline_picker(obs, show, necklines, label=label, color=color)
    if picked:
        nonce = str(picked.get("nonce", ""))
        if nonce and st.session_state.get("last_neckline_nonce") != nonce:
            st.session_state.last_neckline_nonce = nonce
            necklines.append(
                {
                    "label": str(picked.get("label") or label),
                    "price": float(picked["price"]),
                    "color": str(picked.get("color") or color),
                }
            )
            st.rerun()

    if st.button("現在値にラインを追加", width="stretch"):
        necklines.append({"label": label, "price": float(obs["current_price"]), "color": color})
        st.rerun()

    if necklines:
        st.dataframe(
            [{"ラベル": line["label"], "価格": f"{line['price']:,.1f}円"} for line in necklines],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("まだネックラインはありません。")

    delete_col, clear_col, done_col = st.columns(3)
    if delete_col.button("最後のラインを削除", width="stretch", disabled=not bool(necklines)):
        necklines.pop()
        st.rerun()
    if clear_col.button("全ラインを削除", width="stretch", disabled=not bool(necklines)):
        st.session_state.necklines = []
        st.rerun()
    if done_col.button("完了してデイトレードへ", width="stretch", disabled=not bool(necklines)):
        st.session_state.neckline_setup_done = True
        st.rerun()


def _new_env(inputs: dict) -> TradingEnvironment:
    env = TradingEnvironment(
        symbol=inputs["symbol"],
        trading_date=inputs["trading_date"],
        order_quantity=inputs["quantity"],
        initial_cash=inputs["initial_cash"],
        data_source=inputs["data_source"],
        force_refresh=inputs["refresh_data"],
    )
    env.reset()
    return env


def _remember_order_event(action: Action | str, info: dict) -> None:
    if action in {Action.HOLD, "PLAY", "PAUSE"}:
        return
    fill_info = info.get("fill", {})
    fill = fill_info.get("fill")
    if action == "RUN_TO_END" and fill_info.get("status") != "filled":
        return
    if fill_info.get("status") != "filled" or not fill:
        st.session_state.last_order_event = {
            "kind": "ignored",
            "title": "注文は約定しませんでした",
            "detail": fill_info.get("reason", "この注文は現在のポジション状態では実行されませんでした。"),
        }
        return

    fill_action = fill.get("action")
    side = fill.get("side")
    quantity = fill.get("quantity", 0)
    price = fill.get("price", 0.0)
    position_quantity = fill.get("position_quantity")
    average_entry_price = fill.get("average_entry_price")
    pnl = fill.get("pnl")
    if fill_action == "OPEN" and side == "LONG":
        kind, title = "long", "買い建て"
    elif fill_action == "OPEN" and side == "SHORT":
        kind, title = "short", "空売り建て"
    elif fill_action == "CLOSE" and side == "LONG":
        kind, title = "close-long", "買い決済"
    elif fill_action == "CLOSE" and side == "SHORT":
        kind, title = "close-short", "空売り決済"
    else:
        kind, title = "filled", "約定"

    detail = f"{quantity:,}株 / {price:,.1f}円"
    if position_quantity is not None and average_entry_price is not None and pnl is None:
        detail += f" / 建玉 {position_quantity:,}株 / 平均 {average_entry_price:,.1f}円"
    if pnl is not None:
        detail += f" / 損益 {pnl:,.0f}円"
    st.session_state.last_order_event = {"kind": kind, "title": title, "detail": detail}


def _render_order_event() -> None:
    event = st.session_state.get("last_order_event")
    if not event:
        return

    palettes = {
        "long": ("#ecfdf5", "#047857", "#10b981"),
        "short": ("#fef2f2", "#b91c1c", "#ef4444"),
        "close-long": ("#eff6ff", "#1d4ed8", "#60a5fa"),
        "close-short": ("#fff7ed", "#c2410c", "#fb923c"),
        "ignored": ("#f8fafc", "#475569", "#94a3b8"),
        "filled": ("#f5f3ff", "#6d28d9", "#a78bfa"),
    }
    background, foreground, accent = palettes.get(event["kind"], palettes["filled"])
    st.markdown(
        f"""
        <style>
        @keyframes orderFlash {{
          0% {{ transform: scale(0.985); box-shadow: 0 0 0 0 {accent}; }}
          45% {{ transform: scale(1.0); box-shadow: 0 0 0 8px rgba(15, 23, 42, 0.08); }}
          100% {{ transform: scale(1.0); box-shadow: 0 0 0 0 rgba(15, 23, 42, 0); }}
        }}
        .order-flash {{
          animation: orderFlash 900ms ease-out;
          border: 3px solid {accent};
          background: {background};
          color: {foreground};
          padding: 18px 22px;
          margin: 10px 0 18px;
          font-weight: 800;
          border-radius: 8px;
        }}
        .order-flash-title {{
          font-size: 34px;
          line-height: 1.1;
          letter-spacing: 0;
        }}
        .order-flash-detail {{
          font-size: 18px;
          margin-top: 6px;
        }}
        </style>
        <div class="order-flash">
          <div class="order-flash-title">{escape(str(event["title"]))}</div>
          <div class="order-flash-detail">{escape(str(event["detail"]))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _position_text(obs: dict) -> str:
    position = obs["position"]
    if position.is_flat:
        return "建玉なし"
    side = "買い" if position.side == PositionSide.LONG else "空売り"
    return f"{side} {position.quantity:,}株 / 平均 {position.entry_price:,.1f}円"


def _yen(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}円"


def _account_rows(obs: dict) -> list[dict[str, str]]:
    return [
        {"項目": "評価額", "金額": _yen(obs["equity"], 0)},
        {"項目": "入金額", "金額": _yen(obs["initial_cash"], 0)},
        {"項目": "買付余力", "金額": _yen(obs["available_cash"], 0)},
        {"項目": "建玉金額", "金額": _yen(obs["committed_notional"], 0)},
        {"項目": "確定損益", "金額": _yen(obs["realized_pnl"], 0)},
        {"項目": "含み損益", "金額": _yen(obs["unrealized_pnl"], 0)},
    ]


def _trades_display(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["銘柄", "建玉時刻", "決済時刻", "売買", "株数", "建玉価格", "決済価格", "損益"]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    result = pd.DataFrame(
        {
            "銘柄": frame["symbol"],
            "建玉時刻": pd.to_datetime(frame["entry_time"]).dt.strftime("%H:%M"),
            "決済時刻": pd.to_datetime(frame["exit_time"]).dt.strftime("%H:%M"),
            "売買": frame["side"].map({"LONG": "買い", "SHORT": "空売り"}).fillna(frame["side"]),
            "株数": frame["quantity"].map(lambda value: f"{int(value):,}株"),
            "建玉価格": frame["entry_price"].map(lambda value: _yen(float(value), 1)),
            "決済価格": frame["exit_price"].map(lambda value: _yen(float(value), 1)),
            "損益": frame["pnl"].map(lambda value: _yen(float(value), 0)),
        }
    )
    return result[columns]


def main() -> None:
    ensure_project_dirs()
    inputs = render_sidebar()
    st.session_state.setdefault("is_playing", False)
    key = _env_key(inputs)
    _sync_neckline_context(key, reset=inputs["reset"])
    if inputs["reset"] or inputs["refresh_data"] or st.session_state.get("env_key") != key or "env" not in st.session_state:
        try:
            if inputs["reset"]:
                st.session_state.last_order_event = None
                st.session_state.is_playing = False
            spinner_text = (
                f"実データを取得中です... {inputs['symbol']} / {inputs['trading_date'].isoformat()}"
                if inputs["data_source"] == "yahoo"
                else "サンプルデータを準備中です..."
            )
            with st.spinner(spinner_text):
                st.session_state.env = _new_env(inputs)
        except RealDataUnavailable as exc:
            st.error(str(exc))
            st.stop()
        st.session_state.env_key = key

    env: TradingEnvironment = st.session_state.env
    env.order_quantity = inputs["quantity"]
    obs = env._observation()

    st.title("デイトレード練習・自動売買検証シミュレーター")
    st.caption("本アプリは過去の株価データを用いたトレード練習・シミュレーション用アプリです。実際の投資判断を推奨するものではありません。")
    if inputs["data_source"] == "yahoo":
        st.caption(f"データ取得元: Yahooファイナンス / ティッカー: {yahoo_symbol(inputs['symbol'])}")
    else:
        st.caption("データ取得元: サンプル生成データ")

    if not st.session_state.get("neckline_setup_done", False):
        _render_neckline_setup(obs, inputs["show"])
        st.stop()

    action = render_action_buttons(st.session_state.is_playing)
    if action == "PLAY":
        st.session_state.is_playing = True
        st.rerun()
    elif action == "PAUSE":
        st.session_state.is_playing = False
        st.rerun()
    elif action == "RUN_TO_END":
        st.session_state.is_playing = False
        info = {}
        while not env.done:
            obs, _, _, info = env.step(Action.HOLD, inputs["quantity"])
        _remember_order_event(action, info)
    elif action is not None:
        obs, _, _, info = env.step(action, inputs["quantity"])
        _remember_order_event(action, info)
    else:
        obs = env._observation()

    _render_order_event()

    top = st.columns(6)
    display_name = symbol_display_name(inputs["symbol"])
    top[0].metric("銘柄", f"{inputs['symbol']} {display_name}".strip())
    top[1].metric("日付", inputs["trading_date"].isoformat())
    top[2].metric("時刻", obs["timestamp"].strftime("%H:%M"))
    top[3].metric("現在値", _yen(obs["current_price"], 1))
    top[4].metric("確定損益", _yen(obs["realized_pnl"], 0))
    top[5].metric("含み損益", _yen(obs["unrealized_pnl"], 0))

    if inputs["chart_type"].endswith("分足"):
        st.plotly_chart(
            minute_chart(
                obs,
                inputs["show"],
                inputs["display_window"],
                st.session_state.get("necklines", []),
                inputs["chart_type"],
            ),
            width="stretch",
        )
    else:
        st.plotly_chart(
            daily_chart(obs, inputs["show"], inputs["chart_type"], st.session_state.get("necklines", [])),
            width="stretch",
        )

    detail = st.columns(2)
    detail[0].subheader("ポジション")
    detail[0].write(_position_text(obs))
    detail[1].subheader("口座")
    detail[1].dataframe(_account_rows(obs), width="stretch", hide_index=True)

    st.subheader("トレード履歴")
    st.dataframe(_trades_display(env.broker.trades_frame()), width="stretch", hide_index=True)

    interval = _speed_interval_seconds(inputs["speed"])
    if st.session_state.is_playing and interval is not None and not env.done:
        time.sleep(interval)
        env.step(Action.HOLD, inputs["quantity"])
        st.rerun()


if __name__ == "__main__":
    main()
