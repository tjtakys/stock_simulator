import pandas as pd


def vwap(frame: pd.DataFrame) -> pd.Series:
    typical_price = (frame["high"] + frame["low"] + frame["close"]) / 3.0
    volume = frame["volume"].fillna(0)
    cumulative_volume = volume.cumsum()
    weighted_price = (typical_price * volume).cumsum()
    return weighted_price / cumulative_volume.replace(0, pd.NA)
