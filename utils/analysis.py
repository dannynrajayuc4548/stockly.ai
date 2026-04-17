"""Stock analysis utilities for calculating technical indicators and metrics."""

import pandas as pd
import numpy as np


def calculate_moving_averages(df: pd.DataFrame, windows: list = [20, 50, 200]) -> pd.DataFrame:
    """Calculate simple moving averages for given windows.
    
    Args:
        df: DataFrame with 'Close' column
        windows: List of window sizes in days
    
    Returns:
        DataFrame with added SMA columns
    """
    result = df.copy()
    for window in windows:
        if len(df) >= window:
            result[f'SMA_{window}'] = df['Close'].rolling(window=window).mean()
    return result


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI).
    
    Args:
        df: DataFrame with 'Close' column
        period: RSI period (default 14)
    
    Returns:
        Series with RSI values
    """
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Calculate Bollinger Bands.
    
    Args:
        df: DataFrame with 'Close' column
        window: Rolling window size (default 20)
        num_std: Number of standard deviations (default 2)
    
    Returns:
        DataFrame with 'BB_upper', 'BB_middle', 'BB_lower' columns
    """
    result = df.copy()
    result['BB_middle'] = df['Close'].rolling(window=window).mean()
    rolling_std = df['Close'].rolling(window=window).std()
    result['BB_upper'] = result['BB_middle'] + (rolling_std * num_std)
    result['BB_lower'] = result['BB_middle'] - (rolling_std * num_std)
    return result


def calculate_volatility(df: pd.DataFrame, period: int = 30) -> float:
    """Calculate annualized volatility.
    
    Args:
        df: DataFrame with 'Close' column
        period: Number of days for calculation
    
    Returns:
        Annualized volatility as a percentage
    """
    returns = df['Close'].pct_change().dropna()
    if len(returns) < 2:
        return 0.0
    recent_returns = returns.tail(period)
    return float(recent_returns.std() * np.sqrt(252) * 100)


def get_summary_stats(df: pd.DataFrame) -> dict:
    """Compute summary statistics for a stock's historical data.
    
    Args:
        df: DataFrame with OHLCV columns
    
    Returns:
        Dictionary of summary statistics
    """
    if df.empty:
        return {}

    returns = df['Close'].pct_change().dropna()

    return {
        'avg_volume': int(df['Volume'].mean()) if 'Volume' in df.columns else None,
        'high_52w': round(float(df['High'].max()), 2) if 'High' in df.columns else None,
        'low_52w': round(float(df['Low'].min()), 2) if 'Low' in df.columns else None,
        'avg_daily_return': round(float(returns.mean() * 100), 4),
        'volatility_annualized': round(calculate_volatility(df), 2),
        'sharpe_ratio': round(
            float((returns.mean() / returns.std()) * np.sqrt(252)), 4
        ) if returns.std() != 0 else 0.0,
        'max_drawdown': round(float(_max_drawdown(df['Close'])), 4),
    }


def _max_drawdown(prices: pd.Series) -> float:
    """Calculate maximum drawdown from a price series."""
    cumulative = (1 + prices.pct_change()).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    return drawdown.min() * 100
