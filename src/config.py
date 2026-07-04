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
