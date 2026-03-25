"""
data.py — Stock data retrieval layer.
Wraps cache.py calls and returns clean, app-ready data structures.
Designed to be fault-tolerant on Streamlit Cloud where yfinance .info
can be rate-limited or return sparse data.
"""

from __future__ import annotations
import pandas as pd
from backend.cache import (
    cached_ticker_info,
    cached_history,
    cached_news,
    cached_multi_history,
)


# ── Stock detail card ──────────────────────────────────────────────────────

def get_stock_details(ticker: str) -> dict:
    """
    Return a flat dict of key metrics for *ticker*.
    Falls back gracefully — always returns a usable dict as long as
    we can get at least a price from the history data.
    """
    info = cached_ticker_info(ticker)

    def _fmt_cap(val):
        if isinstance(val, (int, float)):
            if val >= 1e12: return f"${val/1e12:.2f}T"
            if val >= 1e9:  return f"${val/1e9:.2f}B"
            if val >= 1e6:  return f"${val/1e6:.2f}M"
        return "N/A"

    # Try to get price from info; if missing fall back to last close from history
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not price:
        hist = cached_history(ticker, "5d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
        else:
            price = 0

    return {
        "name":            info.get("longName") or info.get("shortName") or ticker,
        "sector":          info.get("sector", "N/A"),
        "industry":        info.get("industry", "N/A"),
        "currency":        info.get("currency", "USD"),
        "exchange":        info.get("exchange", "N/A"),
        "price":           float(price),
        "change_pct":      round(float(info.get("regularMarketChangePercent", 0) or 0), 2),
        "market_cap":      _fmt_cap(info.get("marketCap")),
        "pe_ratio":        round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else "N/A",
        "eps":             info.get("trailingEps", "N/A"),
        "high_52w":        info.get("fiftyTwoWeekHigh", "N/A"),
        "low_52w":         info.get("fiftyTwoWeekLow", "N/A"),
        "volume":          info.get("volume", "N/A"),
        "avg_volume":      info.get("averageVolume", "N/A"),
        "dividend_yield":  f"{info.get('dividendYield', 0)*100:.2f}%" if info.get("dividendYield") else "N/A",
        "beta":            round(info.get("beta", 0), 2) if info.get("beta") else "N/A",
        "target_price":    info.get("targetMeanPrice", "N/A"),
        "recommendation":  (info.get("recommendationKey") or "N/A").upper(),
        "description":     info.get("longBusinessSummary", ""),
    }


# ── OHLCV history ──────────────────────────────────────────────────────────

def get_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Return OHLCV DataFrame with a clean DatetimeIndex."""
    df = cached_history(ticker, period)
    if df.empty:
        return df
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.sort_index()


# ── News feed ──────────────────────────────────────────────────────────────

def get_news(ticker: str) -> list[dict]:
    """Return list of news dicts: {title, link, publisher, publish_time}."""
    raw = cached_news(ticker)
    cleaned = []
    for item in raw[:8]:
        cleaned.append({
            "title":        item.get("title", "No title"),
            "link":         item.get("link", "#"),
            "publisher":    item.get("publisher", "Unknown"),
            "publish_time": item.get("providerPublishTime", 0),
        })
    return cleaned


# ── Peer comparison ────────────────────────────────────────────────────────

def get_peer_data(tickers: list[str], period: str = "6mo") -> pd.DataFrame:
    """
    Return a DataFrame where each column is a ticker's normalised
    closing price (rebased to 1.0 at start of period).
    """
    df = cached_multi_history(tuple(tickers), period)
    if df.empty:
        return df
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna(how="any")
    if df.shape[0] < 2:
        return pd.DataFrame()
    return df.div(df.iloc[0])


# ── Sidebar snapshot ───────────────────────────────────────────────────────

WATCHLIST: dict[str, str] = {
    "Apple":     "AAPL",
    "Microsoft": "MSFT",
    "Tesla":     "TSLA",
    "NVIDIA":    "NVDA",
    "Amazon":    "AMZN",
    "Google":    "GOOG",
    "Meta":      "META",
}


def get_daily_snapshot() -> dict[str, dict]:
    """
    Return {name: {price, change_pct}} for each stock in WATCHLIST.
    Uses 5d history to compute intraday change (more reliable on cloud).
    """
    result = {}
    for name, ticker in WATCHLIST.items():
        df = cached_history(ticker, period="5d")
        if df is not None and not df.empty and len(df) >= 2:
            open_p  = float(df["Open"].iloc[-1])
            close_p = float(df["Close"].iloc[-1])
            chg     = ((close_p - open_p) / open_p * 100) if open_p else 0
            result[name] = {"ticker": ticker, "price": close_p, "change_pct": round(chg, 2)}
    return result
