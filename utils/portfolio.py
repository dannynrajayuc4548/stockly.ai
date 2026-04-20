"""Portfolio tracking and analysis utilities for stockly.ai."""

import pandas as pd
import numpy as np
from utils.stock_data import get_historical_data, get_stock_info


def calculate_portfolio_value(holdings: dict) -> dict:
    """
    Calculate current portfolio value and metrics.

    Args:
        holdings: dict of {ticker: {'shares': float, 'avg_cost': float}}

    Returns:
        dict with portfolio summary including total value, gain/loss, weights
    """
    portfolio = []
    total_value = 0.0
    total_cost = 0.0

    for ticker, position in holdings.items():
        info = get_stock_info(ticker)
        if not info or 'current_price' not in info:
            continue

        shares = position.get('shares', 0)
        avg_cost = position.get('avg_cost', 0)
        current_price = info['current_price']

        market_value = shares * current_price
        cost_basis = shares * avg_cost
        gain_loss = market_value - cost_basis
        gain_loss_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

        portfolio.append({
            'ticker': ticker,
            'name': info.get('name', ticker),
            'shares': shares,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'market_value': market_value,
            'cost_basis': cost_basis,
            'gain_loss': gain_loss,
            'gain_loss_pct': gain_loss_pct,
        })

        total_value += market_value
        total_cost += cost_basis

    # Calculate portfolio weights
    for item in portfolio:
        item['weight'] = (item['market_value'] / total_value * 100) if total_value > 0 else 0

    total_gain_loss = total_value - total_cost
    total_gain_loss_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

    return {
        'positions': portfolio,
        'total_value': total_value,
        'total_cost': total_cost,
        'total_gain_loss': total_gain_loss,
        'total_gain_loss_pct': total_gain_loss_pct,
    }


def calculate_portfolio_returns(holdings: dict, period: str = '1y') -> pd.Series:
    """
    Calculate historical portfolio returns based on holdings.

    Args:
        holdings: dict of {ticker: {'shares': float, 'avg_cost': float}}
        period: time period string (e.g. '1y', '6mo')

    Returns:
        pd.Series of daily portfolio returns
    """
    price_data = {}

    for ticker in holdings:
        hist = get_historical_data(ticker, period=period)
        if hist is not None and not hist.empty:
            price_data[ticker] = hist['Close']

    if not price_data:
        return pd.Series(dtype=float)

    prices_df = pd.DataFrame(price_data).dropna()

    # Compute total portfolio value over time using fixed share counts
    portfolio_value = pd.Series(0.0, index=prices_df.index)
    for ticker, col_data in prices_df.items():
        shares = holdings[ticker].get('shares', 0)
        portfolio_value += col_data * shares

    returns = portfolio_value.pct_change().dropna()
    return returns


def calculate_portfolio_stats(returns: pd.Series) -> dict:
    """
    Compute summary statistics for portfolio return series.

    Args:
        returns: pd.Series of daily returns

    Returns:
        dict with annualized return, volatility, Sharpe ratio, max drawdown
    """
    if returns.empty:
        return {}

    annualized_return = returns.mean() * 252
    annualized_vol = returns.std() * np.sqrt(252)
    sharpe_ratio = (annualized_return / annualized_vol) if annualized_vol > 0 else 0

    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    return {
        'annualized_return': round(annualized_return * 100, 2),
        'annualized_volatility': round(annualized_vol * 100, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'max_drawdown': round(max_drawdown * 100, 2),
    }
