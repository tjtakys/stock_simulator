import pandas as pd

from src.indicators.bollinger import bollinger_bands
from src.indicators.moving_average import moving_average
from src.indicators.vwap import vwap


def test_vwap_uses_typical_price_weighted_by_volume():
    frame = pd.DataFrame(
        {
            "high": [11.0, 22.0],
            "low": [9.0, 18.0],
            "close": [10.0, 20.0],
            "volume": [1, 3],
        }
    )

    result = vwap(frame)

    assert result.iloc[0] == 10.0
    assert result.iloc[1] == 17.5


def test_moving_average_uses_available_history():
    result = moving_average(pd.Series([10.0, 20.0, 30.0]), 2)

    assert result.tolist() == [10.0, 15.0, 25.0]


def test_bollinger_bands_return_expected_columns():
    result = bollinger_bands(pd.Series([1.0, 2.0, 3.0]), window=2)

    assert set(result.columns) == {
        "bb_middle",
        "bb_upper_1",
        "bb_lower_1",
        "bb_upper_2",
        "bb_lower_2",
        "bb_upper_3",
        "bb_lower_3",
    }
    assert result["bb_middle"].iloc[-1] == 2.5
