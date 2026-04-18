"""Utility module for fetching and processing stock market data."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_stock_info(ticker: str) -> dict:
    """Fetch basic stock information for a given ticker symbol.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
    
    Returns:
        Dictionary containing stock metadata and current price info.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "symbol": ticker.upper(),
            "name": info.get("longName", "N/A"),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "previous_close": info.get("previousClose", 0),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", None),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
            "volume": info.get("volume", 0),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
        }
    except Exception as e:
        return {"error": str(e), "symbol": ticker.upper()}


def get_historical_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Retrieve historical OHLCV data for a stock.
    
    Args:
        ticker: Stock ticker symbol.
        period: Time period string ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y').
                Changed default to 1y — I find a full year more useful for spotting
                seasonal patterns and longer-term support/resistance levels.
        interval: Data interval ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo').
    
    Returns:
        DataFrame with Open, High, Low, Close, Volume columns.
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        df.index = pd.to_datetime(df.index)
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        return df
    except Exception as e:
        print(f"Error fetching historical data for {ticker}: {e}")
        return pd.DataFrame()


def calculate_price_change(ticker: str) -> dict:
    """Calculate price change and percentage change from previous close.
    
    Args:
        ticker: Stock ticker symbol.
    
    Returns:
        Dictionary with change and percent_change values.
    """
    info = get_stock_info(ticker)
    if "error" in info:
        return info

    current = info["current_price"]
    previous = info["previous_close"]

    if previous and previous != 0:
        change = current - previous
        percent_change = (change / previous) * 100
    else:
        change = 0
        percent_change = 0

    return {
        "symbol": info["symbol"],
        "current_price": current,
        "change": round(change, 4),
        "percent_change": round(percent_change, 2),
        "direction": "up" if change >= 0 else "down",
    }


def search_tickers(query: str) -> list:
    """Search for stock ti