from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def equity_curve_figure(equity: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not equity.empty:
        fig.add_trace(go.Scatter(x=equity["timestamp"], y=equity["equity"], mode="lines", name="Equity"))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
    return fig
