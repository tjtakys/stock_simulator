import pandas as pd


def bollinger_bands(series: pd.Series, window: int = 20) -> pd.DataFrame:
    middle = series.rolling(window=window, min_periods=1).mean()
    std = series.rolling(window=window, min_periods=2).std(ddof=0).fillna(0.0)
    return pd.DataFrame(
        {
            "bb_middle": middle,
            "bb_upper_1": middle + std,
            "bb_lower_1": middle - std,
            "bb_upper_2": middle + 2.0 * std,
            "bb_lower_2": middle - 2.0 * std,
            "bb_upper_3": middle + 3.0 * std,
            "bb_lower_3": middle - 3.0 * std,
        },
        index=series.index,
    )
