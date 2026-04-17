"""Utility functions for generating stock charts and visualizations."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd


def create_price_chart(df: pd.DataFrame, ticker: str, period: str = "1mo") -> go.Figure:
    """Create an interactive candlestick chart with volume overlay.

    Args:
        df: DataFrame with OHLCV data (Open, High, Low, Close, Volume)
        ticker: Stock ticker symbol
        period: Time period string for chart title

    Returns:
        Plotly Figure object
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25]
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1, col=1
    )

    # Volume bar chart
    colors = [
        "#26a69a" if close >= open_ else "#ef5350"
        for close, open_ in zip(df["Close"], df["Open"])
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.7,
        ),
        row=2, col=1
    )

    fig.update_layout(
        title=f"{ticker} — {period} Price History",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=500,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


def create_line_chart(df: pd.DataFrame, ticker: str, period: str = "1mo") -> go.Figure:
    """Create a simple closing price line chart.

    Args:
        df: DataFrame with at least a 'Close' column
        ticker: Stock ticker symbol
        period: Time period string for chart title

    Returns:
        Plotly Figure object
    """
    fig = px.line(
        df,
        x=df.index,
        y="Close",
        title=f"{ticker} — {period} Closing Price",
        template="plotly_dark",
        labels={"Close": "Price (USD)", "index": "Date"},
    )
    fig.update_traces(line_color="#5c6bc0", line_width=2)
    fig.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def create_returns_histogram(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Create a histogram of daily percentage returns.

    Args:
        df: DataFrame with a 'Close' column
        ticker: Stock ticker symbol

    Returns:
        Plotly Figure object
    """
    daily_returns = df["Close"].pct_change().dropna() * 100

    fig = px.histogram(
        daily_returns,
        nbins=40,
        title=f"{ticker} — Daily Returns Distribution",
        template="plotly_dark",
        labels={"value": "Daily Return (%)", "count": "Frequency"},
        color_discrete_sequence=["#5c6bc0"],
    )
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig
