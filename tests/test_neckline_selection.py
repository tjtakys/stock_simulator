from __future__ import annotations

import app


def test_selected_neckline_price_picks_price_layer_from_multiple_points():
    event = {
        "selection": {
            "points": [
                {"curve_number": 0, "point_number": 3, "x": 10, "y": None},
                {
                    "curve_number": 7,
                    "point_number": 42,
                    "point_index": 42,
                    "x": 12,
                    "y": 90234.56,
                    "customdata": [90234.56],
                },
            ]
        }
    }

    selected = app._selected_neckline_price(event)

    assert selected == (90234.6, "7:42:42:12:90234.56")


def test_selected_neckline_price_accepts_tuple_customdata():
    event = {
        "selection": {
            "points": [
                {
                    "curve_number": 7,
                    "point_number": 42,
                    "point_index": 42,
                    "x": 12,
                    "y": 90100.0,
                    "customdata": (90100.0,),
                }
            ]
        }
    }

    selected = app._selected_neckline_price(event)

    assert selected == (90100.0, "7:42:42:12:90100.0")
