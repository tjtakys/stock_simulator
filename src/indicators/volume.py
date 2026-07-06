from __future__ import annotations

import pandas as pd


def add_volume_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    volume = result["volume"].astype(float)
    result["volume_ma_5"] = volume.rolling(window=5, min_periods=1).mean()
    result["volume_ma_25"] = volume.rolling(window=25, min_periods=1).mean()
    result["volume_ratio_5_to_25"] = result["volume_ma_5"] / result["volume_ma_25"].replace(0, pd.NA)
    result["recent_5min_volume"] = volume.rolling(window=5, min_periods=1).sum()
    result["avg_30min_volume"] = volume.rolling(window=30, min_periods=1).sum() / 6.0

    # Spec aliases. Keep the local snake_case names above as the primary API.
    result["volume_ma5"] = result["volume_ma_5"]
    result["volume_ma25"] = result["volume_ma_25"]
    return result
