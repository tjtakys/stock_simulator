from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from io import BytesIO
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

APP_URL = os.environ.get("DEMO_APP_URL", "http://127.0.0.1:8501")
OUTPUT_PATH = ROOT / "docs" / "assets" / "demo.gif"
VIEWPORT = (1440, 1000)
FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"


class WebSocket:
    def __init__(self, url: str) -> None:
        parsed = urllib.request.urlparse(url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 80
        self.path = parsed.path
        if parsed.query:
            self.path += f"?{parsed.query}"
        self.socket = socket.create_connection((self.host, self.port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Origin: http://127.0.0.1:{self.port}\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.socket.sendall(request.encode("ascii"))
        response = self.socket.recv(4096)
        if b" 101 " not in response:
            raise RuntimeError("Chrome DevTools Protocolへの接続に失敗しました。")

    def send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        header = bytearray([0x81])
        length = len(body)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(body))
        self.socket.sendall(header + masked)

    def recv_json(self) -> dict:
        chunks: list[bytes] = []
        while True:
            first, second = self._read_exact(2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            masked = bool(second & 0x80)
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 8:
                raise RuntimeError("Chrome DevTools Protocolとの接続が閉じられました。")
            if opcode in {1, 0}:
                chunks.append(payload)
            if fin:
                return json.loads(b"".join(chunks).decode("utf-8"))

    def close(self) -> None:
        self.socket.close()

    def _read_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise RuntimeError("Chrome DevTools Protocolからの読み込みに失敗しました。")
            data.extend(chunk)
        return bytes(data)


class ChromeSession:
    def __init__(self, ws_url: str) -> None:
        self.ws = WebSocket(ws_url)
        self.next_id = 0

    def call(self, method: str, params: dict | None = None, timeout: float = 15.0) -> dict:
        self.next_id += 1
        message_id = self.next_id
        self.ws.socket.settimeout(timeout)
        self.ws.send_json({"id": message_id, "method": method, "params": params or {}})
        while True:
            message = self.ws.recv_json()
            if message.get("id") != message_id:
                continue
            if "error" in message:
                raise RuntimeError(f"{method} failed: {message['error']}")
            return message.get("result", {})

    def evaluate(self, expression: str) -> object:
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if "exceptionDetails" in result:
            raise RuntimeError(str(result["exceptionDetails"]))
        return result.get("result", {}).get("value")

    def wait_for_text(self, text: str, timeout: float = 25.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if text in self.body_text():
                return
            time.sleep(0.4)
        raise RuntimeError(f"画面に '{text}' が表示されませんでした。")

    def wait_until_text_absent(self, text: str, timeout: float = 25.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if text not in self.body_text():
                return
            time.sleep(0.4)
        raise RuntimeError(f"画面から '{text}' が消えませんでした。")

    def body_text(self) -> str:
        return str(self.evaluate("document.body ? document.body.innerText : ''") or "")

    def current_time(self) -> str | None:
        match = re.search(r"^時刻\s*\n\s*(\d{2}:\d{2})$", self.body_text(), flags=re.MULTILINE)
        return match.group(1) if match else None

    def click_text(self, text: str) -> bool:
        script = f"""
        (() => {{
          const expected = {json.dumps(text)};
          const nodes = Array.from(document.querySelectorAll('button,label,[role="button"],[role="radio"]'));
          const visible = (el) => {{
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
          }};
          for (const el of nodes) {{
            const actual = (el.innerText || el.textContent || '').trim();
            if (actual === expected && visible(el)) {{
              if (el.disabled || el.getAttribute('aria-disabled') === 'true') continue;
              el.scrollIntoView({{block: 'center', inline: 'center'}});
              el.click();
              return true;
            }}
          }}
          return false;
        }})()
        """
        return bool(self.evaluate(script))

    def hover_and_click_plot(self) -> None:
        self.wait_for_plot()
        box = self.evaluate(
            """
            (() => {
              const plot = document.querySelector('.js-plotly-plot');
              if (!plot) return null;
              plot.scrollIntoView({block: 'center', inline: 'center'});
              const rect = plot.getBoundingClientRect();
              return {left: rect.left, top: rect.top, width: rect.width, height: rect.height};
            })()
            """
        )
        if not isinstance(box, dict):
            raise RuntimeError("Plotlyチャートが見つかりませんでした。")
        x = float(box["left"]) + float(box["width"]) * 0.62
        y = float(box["top"]) + float(box["height"]) * 0.52
        self.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        time.sleep(0.5)
        self.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        self.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})

    def click_plot_price(self, price: float) -> None:
        self.wait_for_plot()
        point = self.evaluate(
            f"""
            (() => {{
              const plot = document.querySelector('.js-plotly-plot');
              if (!plot || !plot._fullLayout) return null;
              plot.scrollIntoView({{block: 'center', inline: 'center'}});
              const rect = plot.getBoundingClientRect();
              const xaxis = plot._fullLayout.xaxis;
              const yaxis = plot._fullLayout.yaxis;
              if (!xaxis || !yaxis || !yaxis.l2p) return null;
              const x = rect.left + xaxis._offset + xaxis._length * 0.66;
              const y = rect.top + yaxis._offset + yaxis.l2p({float(price)});
              return {{x, y}};
            }})()
            """
        )
        if not isinstance(point, dict):
            raise RuntimeError("価格クリック用の座標を取得できませんでした。")
        x, y = float(point["x"]), float(point["y"])
        self.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        time.sleep(0.45)
        self.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        self.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})

    def advance_until_time(self, target_time: str, max_steps: int = 100) -> None:
        target_value = _time_to_minutes(target_time)
        for _ in range(max_steps):
            current_time = self.current_time()
            if current_time == target_time:
                return
            if current_time is not None and target_value is not None:
                current_value = _time_to_minutes(current_time)
                if current_value is not None and current_value >= target_value:
                    return
            before_time = current_time
            if not self.click_text("1分進める"):
                time.sleep(0.5)
                continue
            deadline = time.time() + 2.5
            while time.time() < deadline:
                current_time = self.current_time()
                if current_time == target_time:
                    return
                if current_time is not None and current_time != before_time:
                    break
                time.sleep(0.15)
        raise RuntimeError(f"時刻 {target_time} まで進められませんでした。")

    def step_once(self) -> None:
        before_time = self.current_time()
        if not self.click_text("1分進める"):
            raise RuntimeError("1分進めるボタンを押せませんでした。")
        deadline = time.time() + 2.5
        while time.time() < deadline:
            current_time = self.current_time()
            if current_time is not None and current_time != before_time:
                return
            time.sleep(0.15)
        raise RuntimeError("1分送り後の時刻更新を確認できませんでした。")

    def wait_for_plot(self, timeout: float = 25.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            exists = self.evaluate("Boolean(document.querySelector('.js-plotly-plot'))")
            if exists:
                return
            time.sleep(0.4)
        raise RuntimeError("Plotlyチャートが表示されませんでした。")

    def screenshot(self) -> Image.Image:
        result = self.call("Page.captureScreenshot", {"format": "png", "fromSurface": True}, timeout=25.0)
        data = base64.b64decode(result["data"])
        return Image.open(BytesIO(data)).convert("RGB")

    def close(self) -> None:
        self.ws.close()


def main() -> None:
    chrome = _find_chrome()
    port = _free_port()
    profile_dir = Path(tempfile.mkdtemp(prefix="stock-sim-chrome-"))
    command = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-allow-origins=*",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}",
        APP_URL,
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    session: ChromeSession | None = None
    try:
        ws_url = _wait_for_debugger(port)
        session = ChromeSession(ws_url)
        session.call("Page.enable")
        session.call("Runtime.enable")
        session.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": VIEWPORT[0], "height": VIEWPORT[1], "deviceScaleFactor": 1, "mobile": False},
        )
        session.wait_for_text("日足で重要価格ラインを設定")
        session.wait_for_plot()
        line_price = _demo_important_price()
        buy_plan = _demo_buy_plan()

        frames: list[Image.Image] = []
        durations: list[int] = []

        def capture(duration: int = 900, title: str = "", subtitle: str = "", wait: float = 0.6) -> None:
            time.sleep(wait)
            image = session.screenshot()
            if title:
                image = _add_caption(image, title, subtitle)
            frames.append(_resize_for_readme(image))
            durations.append(duration)

        capture(
            1400,
            "1. 日足で重要価格ラインを決める",
            "右側の価格帯別出来高が厚い価格を見て、水平ラインとして登録します。",
        )
        session.click_plot_price(line_price)
        capture(
            1700,
            "価格帯別出来高が多い価格をクリック",
            f"出来高が集中した {line_price:,.0f} 円付近を重要価格ラインに設定しています。",
        )
        if "まだ重要価格ラインはありません" in session.body_text():
            if not session.click_text("現在値にラインを追加"):
                raise RuntimeError("現在値ライン追加ボタンを押せませんでした。")
            capture(900, "重要価格ラインを追加", "クリック価格を水平ラインとして保存します。")
        session.wait_until_text_absent("まだ重要価格ラインはありません")

        if not session.click_text("完了してデイトレードへ"):
            raise RuntimeError("ライン設定完了ボタンを押せませんでした。")
        session.wait_for_text("ポジション")
        session.advance_until_time(str(buy_plan["entry_time"]), max_steps=int(buy_plan["entry_index"]) + 12)
        capture(
            1100,
            "2. デイトレード画面へ",
            f"{buy_plan['entry_time']} の買い場面まで進めます。",
        )

        session.click_text("買い")
        session.wait_for_text("買い建て")
        capture(
            1400,
            "買いエントリー",
            f"{buy_plan['entry_price']:,.0f} 円で買い。ここから60倍速で値動きを再生します。",
        )

        capture(
            900,
            "60倍速で値動きを進める",
            "サイドバーの再生速度は60倍速。短時間で値動きを確認します。",
            wait=0.6,
        )

        for index, target_time in enumerate(buy_plan["playback_times"]):
            session.advance_until_time(str(target_time), max_steps=6)
            capture(
                1050,
                "60倍速でデイトレードを再生中",
                f"{target_time} まで進み、含み益が増えていく様子を確認します。",
                wait=0.35 if index else 0.5,
            )

        close_filled = False
        for attempt in range(4):
            if not session.click_text("決済"):
                time.sleep(0.5)
                continue
            try:
                session.wait_for_text("買い決済", timeout=8.0)
                close_filled = True
                break
            except RuntimeError:
                if attempt == 3:
                    raise
        if not close_filled:
            raise RuntimeError("買い決済を確認できませんでした。")
        capture(
            1900,
            "利益確定",
            "上昇後に決済し、トレード履歴へ損益を記録します。",
        )

        _save_gif(frames, durations, OUTPUT_PATH)
        print(f"saved {OUTPUT_PATH}")
    finally:
        if session is not None:
            session.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


def _find_chrome() -> str:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise RuntimeError("Google Chromeが見つかりませんでした。")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_debugger(port: int) -> str:
    deadline = time.time() + 20
    url = f"http://127.0.0.1:{port}/json"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                targets = json.loads(response.read().decode("utf-8"))
            for target in targets:
                ws_url = target.get("webSocketDebuggerUrl")
                if ws_url and target.get("type") == "page":
                    return str(ws_url)
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("Chromeのデバッグポートに接続できませんでした。")


def _resize_for_readme(image: Image.Image) -> Image.Image:
    target_width = 960
    height = round(image.height * (target_width / image.width))
    resized = image.resize((target_width, height), Image.Resampling.LANCZOS)
    return resized.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)


def _add_caption(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    result = image.convert("RGBA")
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    title_font = _font(36)
    subtitle_font = _font(22)
    margin = 28
    box_height = 112 if subtitle else 78
    draw.rounded_rectangle(
        [margin, margin, result.width - margin, margin + box_height],
        radius=16,
        fill=(15, 23, 42, 222),
    )
    draw.text((margin + 26, margin + 18), title, font=title_font, fill=(255, 255, 255, 255))
    if subtitle:
        draw.text((margin + 28, margin + 65), subtitle, font=subtitle_font, fill=(219, 234, 254, 255))
    return Image.alpha_composite(result, overlay).convert("RGB")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONT_PATH, size=size)
    except OSError:
        return ImageFont.load_default()


def _time_to_minutes(value: str) -> int | None:
    match = re.fullmatch(r"(\d{2}):(\d{2})", value)
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def _demo_important_price() -> float:
    from src.config import DEFAULT_SYMBOL, default_trading_date
    from src.data.providers.yahoo import yahoo_daily_data_path
    from src.ui.chart import _price_axis_range, _volume_profile, long_term_chart_frame

    trading_date = default_trading_date()
    daily = pd.read_csv(yahoo_daily_data_path(DEFAULT_SYMBOL), parse_dates=["date"])
    frame = long_term_chart_frame(daily[daily["date"].dt.date < trading_date], "日足").tail(60)
    y_range = _price_axis_range(frame, {"daily_ma": True, "bollinger": True}, [])
    profile = _volume_profile(frame, y_range)
    if profile is None:
        return float(frame["close"].iloc[-1])
    volume_price_pairs = zip(profile["volumes"], profile["prices"], strict=True)
    return float(max(volume_price_pairs, key=lambda item: item[0])[1])


def _demo_buy_plan() -> dict[str, object]:
    from src.config import DEFAULT_SYMBOL, default_trading_date
    from src.data.providers.yahoo import yahoo_minute_data_path

    trading_date = default_trading_date()
    minute = pd.read_csv(yahoo_minute_data_path(DEFAULT_SYMBOL, trading_date), parse_dates=["timestamp"])
    horizon = 8
    best: tuple[float, int, int] | None = None
    for index in range(0, min(len(minute) - horizon - 1, 180)):
        pnl = float(minute.iloc[index + horizon]["close"] - minute.iloc[index]["close"])
        if best is None or pnl > best[0]:
            best = (pnl, index, horizon)
    if best is None:
        raise RuntimeError("デモ用の買い場面を決められませんでした。")
    _, entry_index, horizon = best
    entry = minute.iloc[entry_index]
    exit_bar = minute.iloc[entry_index + horizon]
    playback_indexes = [
        entry_index + offset
        for offset in [2, 4, 6, horizon]
        if entry_index + offset <= entry_index + horizon
    ]
    return {
        "entry_index": entry_index,
        "exit_index": entry_index + horizon,
        "entry_time": pd.Timestamp(entry["timestamp"]).strftime("%H:%M"),
        "entry_price": float(entry["close"]),
        "exit_time": pd.Timestamp(exit_bar["timestamp"]).strftime("%H:%M"),
        "exit_price": float(exit_bar["close"]),
        "playback_times": [
            pd.Timestamp(minute.iloc[index]["timestamp"]).strftime("%H:%M") for index in playback_indexes
        ],
    }


def _save_gif(frames: list[Image.Image], durations: list[int], path: Path) -> None:
    if not frames:
        raise RuntimeError("GIFにするフレームがありません。")
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == "__main__":
    main()
