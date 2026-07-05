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
from src.strategies.base import get_strategy
from src.ui.chart import daily_chart, important_price_line_chart, minute_chart
from src.ui.controls import render_action_buttons
from src.ui.neckline_picker import NECKLINE_COLORS, NECKLINE_LABELS
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
        "120x": 0.5,
        "240x": 0.25,
    }[speed]


def _strategy_display_name(strategy_name: str) -> str:
    return {
        "bollinger_next_reversion": "ボリンジャー3σ逆張り",
        "bollinger_reversion": "ボリンジャー逆張り",
        "vwap_ma_breakout": "VWAP + 移動平均ブレイクアウト",
        "combined_rule": "複合ルール",
    }.get(strategy_name, strategy_name)


def _autoplay_sleep_seconds(env: TradingEnvironment, interval: float) -> float:
    engine = env.engine
    if engine.index >= len(engine.minute_bars) - 1:
        return interval
    current_timestamp = pd.Timestamp(engine.minute_bars.iloc[engine.index]["timestamp"])
    next_timestamp = pd.Timestamp(engine.minute_bars.iloc[engine.index + 1]["timestamp"])
    gap_seconds = (next_timestamp - current_timestamp).total_seconds()
    if gap_seconds > 30 * 60:
        return 5.0
    return interval


def _sync_neckline_context(key: tuple, reset: bool = False) -> None:
    if reset or st.session_state.get("neckline_context") != key:
        st.session_state.neckline_context = key
        st.session_state.necklines = []
        st.session_state.neckline_setup_done = False
        st.session_state.last_neckline_selection = None


def _render_neckline_setup(obs: dict, show: dict[str, bool]) -> None:
    st.subheader("日足で重要価格ラインを設定")
    st.info("デイトレードを始める前に、日足チャート上で意識したい価格をクリックして水平ラインを追加してください。")

    necklines = st.session_state.setdefault("necklines", [])

    label_col, custom_col, color_col = st.columns([1.1, 1.3, 0.7])
    selected_label = label_col.selectbox("ラベル候補", NECKLINE_LABELS, index=0)
    custom_label = custom_col.text_input("ラベル名", value=selected_label, key=f"neckline_label_{selected_label}")
    label = custom_label.strip() or selected_label
    color_name = color_col.selectbox("色", list(NECKLINE_COLORS), index=0)
    color = NECKLINE_COLORS[color_name]

    chart_slot = st.empty()
    date_range = _render_daily_range_slider(obs)
    st.caption("日足表示範囲バーを左右に動かすと、日足チャートと価格帯別出来高をその範囲で再表示します。")
    with chart_slot.container():
        event = st.plotly_chart(
            important_price_line_chart(obs, show, necklines, date_range),
            width="stretch",
            theme=None,
            key="neckline_selection_chart",
            on_select="rerun",
            selection_mode="points",
            config={"displayModeBar": True, "scrollZoom": True},
        )
    selected = _selected_neckline_price(event)
    if selected is not None:
        price, identity = selected
        if identity != st.session_state.get("last_neckline_selection"):
            st.session_state.last_neckline_selection = identity
            necklines.append(
                {
                    "label": label,
                    "price": price,
                    "color": color,
                }
            )
            st.rerun()

    if necklines:
        st.dataframe(
            [{"ラベル": line["label"], "価格": f"{line['price']:,.1f}円"} for line in necklines],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("まだ重要価格ラインはありません。")

    delete_col, clear_col, done_col = st.columns(3)
    if delete_col.button("最後のラインを削除", width="stretch", disabled=not bool(necklines)):
        necklines.pop()
        st.session_state.last_neckline_selection = None
        st.rerun()
    if clear_col.button("全ラインを削除", width="stretch", disabled=not bool(necklines)):
        st.session_state.necklines = []
        st.session_state.last_neckline_selection = None
        st.rerun()
    if done_col.button("完了してデイトレードへ", width="stretch", disabled=not bool(necklines)):
        st.session_state.neckline_setup_done = True
        st.rerun()


def _daily_range_key(obs: dict) -> str:
    return f"daily_line_range_{obs['symbol']}_{obs['date'].isoformat()}"


def _daily_range_slider_key(obs: dict) -> str:
    key = _daily_range_key(obs)
    version = int(st.session_state.get(f"{key}_slider_version", 0))
    return f"{key}_slider_{version}"


def _daily_range_state(obs: dict) -> tuple[int, int] | None:
    daily = obs["daily_bars"]
    if daily.empty:
        return None

    dates = pd.to_datetime(daily["date"]).dt.date.reset_index(drop=True)
    min_index = 0
    max_index = len(dates) - 1
    if min_index >= max_index:
        return (min_index, max_index)

    default_start = max(len(dates) - 60, 0)
    key = _daily_range_key(obs)
    current_value = st.session_state.get(key, (default_start, max_index))

    if (
        not isinstance(current_value, tuple)
        or len(current_value) != 2
        or not all(isinstance(value, int) for value in current_value)
    ):
        current_value = (default_start, max_index)

    start_index, end_index = sorted((int(current_value[0]), int(current_value[1])))
    start_index = max(start_index, min_index)
    end_index = min(end_index, max_index)
    st.session_state[key] = (start_index, end_index)
    return (start_index, end_index)


def _render_daily_range_slider(obs: dict) -> tuple[int, int] | None:
    current_range = _daily_range_state(obs)
    if current_range is None:
        return None

    daily = obs["daily_bars"]
    dates = pd.to_datetime(daily["date"]).dt.date.reset_index(drop=True)
    if len(dates) <= 1:
        return current_range

    key = _daily_range_key(obs)
    slider_key = _daily_range_slider_key(obs)

    date_options = dates.tolist()
    index_by_date = {date_value: index for index, date_value in enumerate(date_options)}
    selected_dates = st.select_slider(
        "日足表示範囲",
        options=date_options,
        value=(date_options[current_range[0]], date_options[current_range[1]]),
        format_func=lambda value: value.isoformat(),
        key=slider_key,
        width="stretch",
    )
    selected_range = tuple(
        sorted(
            (
                int(index_by_date[selected_dates[0]]),
                int(index_by_date[selected_dates[1]]),
            )
        )
    )
    if selected_range != current_range:
        st.session_state[key] = selected_range
        current_range = selected_range

    if st.button("直近60営業日に戻す", width="stretch"):
        selected_range = (max(len(dates) - 60, 0), len(dates) - 1)
        st.session_state[key] = selected_range
        st.session_state[f"{key}_slider_version"] = int(st.session_state.get(f"{key}_slider_version", 0)) + 1
        st.rerun()

    st.caption(f"選択範囲: {dates.iloc[selected_range[0]].isoformat()} 〜 {dates.iloc[selected_range[1]].isoformat()}")
    return selected_range


def _selected_neckline_price(event: dict) -> tuple[float, str] | None:
    points = event.get("selection", {}).get("points", []) if event else []
    if not points:
        return None
    point = _selected_price_point(points)
    if point is None:
        return None
    customdata = point.get("customdata")
    if isinstance(customdata, list | tuple) and customdata:
        price = customdata[0]
    else:
        price = point.get("y")
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    price = round(float(price), 1)
    identity = ":".join(
        str(point.get(key, ""))
        for key in ["curve_number", "point_number", "point_index", "x", "y"]
    )
    return price, identity


def _selected_price_point(points: list[dict]) -> dict | None:
    for point in reversed(points):
        customdata = point.get("customdata")
        if isinstance(customdata, list | tuple) and customdata:
            try:
                float(customdata[0])
            except (TypeError, ValueError):
                continue
            return point
    for point in reversed(points):
        try:
            float(point.get("y"))
        except (TypeError, ValueError):
            continue
        return point
    return None


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


def _auto_trade_action(inputs: dict, obs: dict) -> Action:
    action, _ = _auto_trade_decision(inputs, obs)
    return action


def _auto_trade_decision(inputs: dict, obs: dict) -> tuple[Action, float | None]:
    if not inputs.get("auto_trade"):
        return Action.HOLD, None
    strategy = get_strategy(inputs["auto_strategy"])
    action = strategy.decide(obs)
    return action, strategy.execution_price(obs, action)


def _remember_auto_action(action: Action) -> None:
    labels = {
        Action.BUY: "買い",
        Action.SELL: "空売り",
        Action.CLOSE: "決済",
        Action.HOLD: "見送り",
    }
    st.session_state.last_auto_action = labels[action]


def _render_auto_trade_status(inputs: dict) -> None:
    if not inputs.get("auto_trade"):
        return
    action_text = st.session_state.get("last_auto_action", "待機")
    mode_text = " / 一括検証モードON" if inputs.get("batch_mode") else ""
    st.info(f"自動売買: {_strategy_display_name(inputs['auto_strategy'])} / 直近判断: {action_text}{mode_text}")


def _run_to_end(env: TradingEnvironment, inputs: dict) -> dict:
    steps = 0
    fills_before = len(env.broker.fills)
    trades_before = len(env.broker.trades)
    started_at = env._observation()["timestamp"]
    info = {}
    executed_action: Action = Action.HOLD
    while not env.done:
        executed_action, execution_price = _auto_trade_decision(inputs, env._observation())
        _remember_auto_action(executed_action)
        _, _, _, info = env.step(executed_action, inputs["quantity"], execution_price=execution_price)
        steps += 1

    obs = env._observation()
    account = info.get("account") or env.broker.get_account(obs["current_price"])
    new_trades = env.broker.trades[trades_before:]
    wins = sum(1 for trade in new_trades if trade.pnl > 0)
    trade_count = len(new_trades)
    st.session_state.batch_result = {
        "strategy": _strategy_display_name(inputs["auto_strategy"]) if inputs.get("auto_trade") else "自動売買なし",
        "started_at": started_at,
        "ended_at": obs["timestamp"],
        "steps": steps,
        "fills": len(env.broker.fills) - fills_before,
        "trades": trade_count,
        "win_rate": (wins / trade_count * 100) if trade_count else 0.0,
        "total_pnl": account["realized_pnl"] + account["unrealized_pnl"],
        "executed_action": executed_action,
        "last_info": info,
    }
    return obs


def _render_batch_result() -> None:
    result = st.session_state.get("batch_result")
    if not result:
        return
    st.success(
        "一括検証完了: "
        f"{result['strategy']} / "
        f"{result['started_at'].strftime('%H:%M')}から{result['ended_at'].strftime('%H:%M')}まで / "
        f"{result['steps']:,}分実行 / "
        f"約定{result['fills']:,}件 / "
        f"トレード{result['trades']:,}件 / "
        f"勝率{result['win_rate']:.1f}% / "
        f"損益 {_yen(result['total_pnl'], 0)}"
    )


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


def _render_account_summary(obs: dict) -> None:
    account_cols = st.columns(3)
    account_cols[0].metric("評価額", _yen(obs["equity"], 0))
    account_cols[1].metric("買付余力", _yen(obs["available_cash"], 0))
    account_cols[2].metric("建玉金額", _yen(obs["committed_notional"], 0))


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
                st.session_state.last_auto_action = None
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

    use_necklines = bool(inputs.get("use_necklines", True))
    if use_necklines and not st.session_state.get("neckline_setup_done", False):
        _render_neckline_setup(obs, inputs["show"])
        st.stop()
    active_necklines = st.session_state.get("necklines", []) if use_necklines else []

    action = render_action_buttons(st.session_state.is_playing)
    _render_auto_trade_status(inputs)
    if inputs.get("batch_run") or (action == "PLAY" and inputs.get("batch_mode")):
        action = "RUN_TO_END"

    if action == "PLAY":
        st.session_state.batch_result = None
        st.session_state.is_playing = True
        st.rerun()
    elif action == "PAUSE":
        st.session_state.is_playing = False
        st.rerun()
    elif action == "RESET_REPLAY":
        st.session_state.is_playing = False
        st.session_state.last_order_event = None
        st.session_state.last_auto_action = None
        st.session_state.batch_result = None
        obs = env.reset()
    elif action == "STEP_BACK":
        st.session_state.is_playing = False
        st.session_state.last_order_event = None
        st.session_state.last_auto_action = None
        st.session_state.batch_result = None
        obs = env.retreat()
    elif action == "RUN_TO_END":
        st.session_state.is_playing = False
        st.session_state.last_auto_action = None
        obs = _run_to_end(env, inputs)
        result = st.session_state.get("batch_result", {})
        last_info = result.get("last_info", {})
        executed_action = result.get("executed_action", Action.HOLD)
        _remember_order_event(executed_action if inputs.get("auto_trade") else action, last_info)
    elif action is not None:
        st.session_state.batch_result = None
        execution_price = None
        if inputs.get("auto_trade") and action == Action.HOLD:
            executed_action, execution_price = _auto_trade_decision(inputs, obs)
        else:
            executed_action = action
        if inputs.get("auto_trade") and action == Action.HOLD:
            _remember_auto_action(executed_action)
        obs, _, _, info = env.step(executed_action, inputs["quantity"], execution_price=execution_price)
        _remember_order_event(executed_action, info)
    else:
        obs = env._observation()

    _render_order_event()
    _render_batch_result()

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
                active_necklines,
                inputs["chart_type"],
            ),
            width="stretch",
            theme=None,
        )
    else:
        st.plotly_chart(
            daily_chart(obs, inputs["show"], inputs["chart_type"], active_necklines),
            width="stretch",
            theme=None,
        )

    detail = st.columns(2)
    detail[0].subheader("ポジション")
    detail[0].write(_position_text(obs))
    detail[1].subheader("口座")
    with detail[1]:
        _render_account_summary(obs)

    st.subheader("トレード履歴")
    st.dataframe(_trades_display(env.broker.trades_frame()), width="stretch", hide_index=True)

    interval = _speed_interval_seconds(inputs["speed"])
    if st.session_state.is_playing and interval is not None and not env.done:
        time.sleep(_autoplay_sleep_seconds(env, interval))
        auto_action, execution_price = _auto_trade_decision(inputs, env._observation())
        _remember_auto_action(auto_action)
        _, _, _, info = env.step(auto_action, inputs["quantity"], execution_price=execution_price)
        _remember_order_event(auto_action, info)
        st.rerun()


if __name__ == "__main__":
    main()
