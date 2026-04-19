"""Sentiment analysis utilities for stock news and social media data."""

import requests
from datetime import datetime, timedelta
from typing import Optional
import re


def get_news_sentiment(ticker: str, api_key: Optional[str] = None) -> dict:
    """
    Fetch recent news headlines for a ticker and compute aggregate sentiment.
    Falls back to a neutral result if no API key is provided.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL')
        api_key: NewsAPI key (optional)

    Returns:
        dict with keys: headlines, scores, average_score, label
    """
    if not api_key:
        return {
            "headlines": [],
            "scores": [],
            "average_score": 0.0,
            "label": "Neutral",
            "note": "No API key provided. Set NEWSAPI_KEY to enable sentiment analysis.",
        }

    from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={ticker}&from={from_date}&sortBy=publishedAt"
        f"&language=en&pageSize=20&apiKey={api_key}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        articles = response.json().get("articles", [])
    except Exception:
        return {
            "headlines": [],
            "scores": [],
            "average_score": 0.0,
            "label": "Neutral",
            "note": "Failed to fetch news data.",
        }

    headlines = [a["title"] for a in articles if a.get("title")]
    scores = [_simple_sentiment_score(h) for h in headlines]
    avg = sum(scores) / len(scores) if scores else 0.0

    return {
        "headlines": headlines,
        "scores": scores,
        "average_score": round(avg, 4),
        "label": _score_to_label(avg),
    }


def _simple_sentiment_score(text: str) -> float:
    """
    Compute a naive sentiment score for a headline using keyword matching.
    Returns a float in [-1.0, 1.0].
    """
    positive_words = [
        "surge", "gain", "rise", "rally", "beat", "profit", "growth",
        "bullish", "upgrade", "outperform", "record", "strong", "up",
        "positive", "boost", "soar", "high", "win", "success",
    ]
    negative_words = [
        "drop", "fall", "loss", "decline", "miss", "bearish", "downgrade",
        "underperform", "weak", "down", "negative", "crash", "low",
        "risk", "warn", "cut", "sell", "fear", "concern",
    ]

    text_lower = re.sub(r"[^a-z ]", "", text.lower())
    words = text_lower.split()

    pos = sum(1 for w in words if w in positive_words)
    neg = sum(1 for w in words if w in negative_words)

    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 4)


def _score_to_label(score: float) -> str:
    """Convert a numeric sentiment score to a human-readable label."""
    if score > 0.15:
        return "Positive"
    elif score < -0.15:
        return "Negative"
    return "Neutral"


def sentiment_color(label: str) -> str:
    """Return a color string for Streamlit display based on sentiment label."""
    colors = {
        "Positive": "green",
        "Negative": "red",
        "Neutral": "gray",
    }
    return colors.get(label, "gray")
