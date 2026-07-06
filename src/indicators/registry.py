from __future__ import annotations

import pandas as pd

from src.indicators.bollinger import bollinger_bands
from src.indicators.moving_average import moving_average
from src.indicators.volume import add_volume_indicators
from src.indicators.vwap import vwap


def add_minute_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["vwap"] = vwap(result)
    result["ma_5"] = moving_average(result["close"], 5)
    result["ma_25"] = moving_average(result["close"], 25)
    result["ma_75"] = moving_average(result["close"], 75)
    bands = bollinger_bands(result["close"], 20)
    for column in bands.columns:
        result[column] = bands[column]
    result = add_volume_indicators(result)
    return result


def add_daily_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["daily_ma_5"] = moving_average(result["close"], 5)
    result["daily_ma_25"] = moving_average(result["close"], 25)
    result["daily_ma_75"] = moving_average(result["close"], 75)
    result["daily_volume_ma_20"] = moving_average(result["volume"], 20)
    return result
