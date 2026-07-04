import csv
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_MINUTE_DIR = RAW_DATA_DIR / "minute"
RAW_DAILY_DIR = RAW_DATA_DIR / "daily"
OUTPUTS_DIR = ROOT_DIR / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
TRADES_DIR = OUTPUTS_DIR / "trades"
EQUITY_DIR = OUTPUTS_DIR / "equity"

DEFAULT_SYMBOL = "285A"
SYMBOL_NAMES = {
    "285A": "キオクシアホールディングス",
}
DEFAULT_SYMBOL_NAME = SYMBOL_NAMES[DEFAULT_SYMBOL]
DEFAULT_DATE = "2026-06-24"
DEFAULT_INITIAL_CASH = 10_000_000.0
DEFAULT_ORDER_QUANTITY = 100


def default_trading_date() -> date:
    cached_date = latest_cached_yahoo_daily_date(DEFAULT_SYMBOL)
    if cached_date is not None:
        return cached_date
    return _previous_weekday(date.today())


def latest_cached_yahoo_daily_date(symbol: str) -> date | None:
    path = RAW_DATA_DIR / "yahoo" / "daily" / f"{symbol.upper()}_daily.csv"
    if not path.exists():
        return None

    latest: date | None = None
    try:
        with path.open(newline="", encoding="utf-8") as csv_file:
            for row in csv.DictReader(csv_file):
                value = row.get("date")
                if not value:
                    continue
                parsed = datetime.fromisoformat(value).date()
                latest = parsed if latest is None else max(latest, parsed)
    except (OSError, ValueError):
        return None
    return latest


def _previous_weekday(value: date) -> date:
    current = value
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def symbol_display_name(symbol: str) -> str:
    return SYMBOL_NAMES.get(symbol.upper(), "")


def ensure_project_dirs() -> None:
    for path in [
        RAW_MINUTE_DIR,
        RAW_DAILY_DIR,
        DATA_DIR / "processed" / "minute",
        DATA_DIR / "processed" / "daily",
        REPORTS_DIR,
        TRADES_DIR,
        EQUITY_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
