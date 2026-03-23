# ============================================================
# STOCKLY — AI ADDON
# File: ai_addon.py  (same folder as stock dashboard.py)
# In stock dashboard.py add at top: from ai_addon import *
# ============================================================


# ─────────────────────────────────────────────────────────────
# 1. IMPORTS
# ─────────────────────────────────────────────────────────────

import requests
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ─────────────────────────────────────────────────────────────
# 2. OLLAMA CONFIG  (key from .streamlit/secrets.toml)
# ─────────────────────────────────────────────────────────────

OLLAMA_API_URL = "https://api.ollama.com/api/chat"
OLLAMA_API_KEY = st.secrets["OLLAMA_API_KEY"]
AI_MODEL       = "gemma3:27b"   # fixed model


# ─────────────────────────────────────────────────────────────
# 3. AI FUNCTIONS  (receive already-cached data, no new calls)
# ─────────────────────────────────────────────────────────────

def ollama_call(prompt: str, system: str) -> str:
    """Single call to Ollama cloud via requests."""
    payload = {
        "model":  AI_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        r = requests.post(OLLAMA_API_URL, json=payload, headers=headers, timeout=45)
        r.raise_for_status()
        return r.json()["message"]["content"]
    except requests.exceptions.Timeout:
        return '{"error": "Request timed out."}'
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'


def parse_json(raw: str) -> dict:
    """Safely strip markdown fences and parse JSON."""
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception:
        return {"error": raw}


# ── AI Function 1: Ticker prediction ─────────────────────────
# Uses: details + history from fetch_stock_details() (already cached)

def ai_ticker_prediction(ticker: str, details: dict, history: pd.DataFrame) -> dict:
    closes   = history["Close"].tail(30).round(2).tolist()
    highs    = history["High"].tail(30).round(2).tolist()
    lows     = history["Low"].tail(30).round(2).tolist()
    avg_30   = round(sum(closes) / len(closes), 2) if closes else 0
    momentum = round(closes[-1] - closes[0], 2) if len(closes) >= 2 else 0

    prompt = f"""
Predict the next 7 trading days for {ticker} using this cached OHLC data.

Current price   : ${details.get('price', 'N/A')}
30-day closes   : {closes}
30-day highs    : {highs}
30-day lows     : {lows}
30-day avg      : ${avg_30}
Momentum        : ${momentum}
52W High / Low  : ${details.get('high_52w','N/A')} / ${details.get('low_52w','N/A')}
PE Ratio        : {details.get('pe_ratio','N/A')}
Analyst score   : {details.get('analyst_mean','N/A')} (1=Strong Buy, 5=Sell)

Return EXACTLY this JSON (no extra text):
{{
  "signal":           "BUY" or "HOLD" or "SELL",
  "confidence":       "High" or "Medium" or "Low",
  "outlook":          "Bullish" or "Bearish" or "Neutral",
  "support":          <number>,
  "resistance":       <number>,
  "predicted_closes": [<day1>, <day2>, <day3>, <day4>, <day5>, <day6>, <day7>],
  "summary":          "3 sentences using the actual numbers."
}}"""
    raw = ollama_call(prompt, "You are a quantitative analyst and technical forecaster. Respond only in valid JSON.")
    return parse_json(raw)


# ── AI Function 2: Top 5 tickers today ───────────────────────
# Uses: details dict from fetch_stock_details() for each ticker (already cached)

def ai_top5_analysis(top5_data: dict) -> dict:
    lines = []
    for ticker, (det, _) in top5_data.items():
        lines.append(
            f"{ticker}: price=${det.get('price','N/A')}, "
            f"change={det.get('change_pct',0):.2f}%, "
            f"pe={det.get('pe_ratio','N/A')}, "
            f"analyst={det.get('analyst_mean','N/A')}"
        )

    prompt = f"""
Analyze today's performance for these 5 stocks. Reply ONLY with valid JSON.

{chr(10).join(lines)}

Return EXACTLY this JSON:
{{
  "AAPL": {{"signal": "BUY or HOLD or SELL", "one_line": "one sentence analysis"}},
  "MSFT": {{"signal": "BUY or HOLD or SELL", "one_line": "one sentence analysis"}},
  "NVDA": {{"signal": "BUY or HOLD or SELL", "one_line": "one sentence analysis"}},
  "TSLA": {{"signal": "BUY or HOLD or SELL", "one_line": "one sentence analysis"}},
  "META": {{"signal": "BUY or HOLD or SELL", "one_line": "one sentence analysis"}}
}}"""
    raw = ollama_call(prompt, "You are a stock analyst. Respond only in valid JSON.")
    return parse_json(raw)


# ── AI Function 3: Market sentiment today ────────────────────
# Uses: news list from fetch_news() (already cached)

def ai_market_sentiment(all_headlines: list) -> dict:
    headlines_text = "\n".join([f"- {h}" for h in all_headlines[:15]])

    prompt = f"""
Assess overall stock market sentiment from these headlines. Reply ONLY with valid JSON.

{headlines_text}

Return EXACTLY this JSON:
{{
  "overall":    "Bullish" or "Bearish" or "Neutral",
  "score":      <integer 0-100>,
  "fear_greed": "Fear" or "Greed" or "Neutral",
  "theme":      "One sentence on the dominant market theme today.",
  "summary":    "2-3 sentences on what this means for investors."
}}"""
    raw = ollama_call(prompt, "You are a market sentiment analyst. Respond only in valid JSON.")
    return parse_json(raw)


# ── AI Function 4: Portfolio health ──────────────────────────
# Uses: portfolio df already computed in tab5 (already cached)

def ai_portfolio_health(portfolio_df: pd.DataFrame,
                         total_invested: float,
                         total_value: float) -> dict:
    if portfolio_df.empty:
        return {"grade": "N/A", "overview": "No holdings found.",
                "risks": [], "tips": [], "verdict": "", "sub_scores": {}}

    total_gain     = total_value - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0

    df = portfolio_df.copy()
    df["weight"] = (df["BALANCE"] / total_value * 100) if total_value > 0 else 0

    rows = "\n".join([
        f"  {r['ASSET']}: {r['DETAIL']} | "
        f"Value ${r['BALANCE']:.2f} | Weight {r['weight']:.1f}% | "
        f"Gain ${r['GAIN']:.2f} ({r['GAIN_PCT']:.1f}%)"
        for _, r in df.iterrows()
    ])

    prompt = f"""
Grade this portfolio A to F. Reply ONLY with valid JSON.

Invested : ${total_invested:.2f} | Value : ${total_value:.2f} | P&L : ${total_gain:.2f} ({total_gain_pct:.1f}%)
Holdings : {len(df)}

{rows}

Return EXACTLY this JSON:
{{
  "grade": "A" or "B" or "C" or "D" or "F",
  "sub_scores": {{
    "diversification": <0-10>,
    "performance":     <0-10>,
    "risk_management": <0-10>
  }},
  "overview": "2 sentences on portfolio health.",
  "risks":    ["risk 1", "risk 2"],
  "tips":     ["tip 1",  "tip 2"],
  "verdict":  "One sentence summary."
}}"""
    raw = ollama_call(prompt, "You are a portfolio risk analyst. Respond only in valid JSON.")
    return parse_json(raw)


# ─────────────────────────────────────────────────────────────
# 4. UI — render_ai_tab()
#
# In stock dashboard.py:
#   1. Add "AI Insights" to st.tabs()
#   2. with tab_ai:
#        render_ai_tab(
#            selected_ticker, details, history,
#            portfolio_df, total_invested, total_value,
#            fetch_stock_details_fn=fetch_stock_details,
#            fetch_news_fn=fetch_news
#        )
# ─────────────────────────────────────────────────────────────


def generate_pdf_report(selected_ticker, pred_result, pred_history,
                         top5_result, top5_raw,
                         market_sentiment, health_result,
                         portfolio_df) -> bytes:
    """
    Builds a full PDF report from all AI analysis results.
    Includes plotly charts exported as images.
    Returns PDF as bytes for st.download_button.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    styles  = getSampleStyleSheet()
    story   = []
    W, H    = A4
    usable_w = W - 4*cm

    # ── Custom styles ────────────────────────────────────────
    title_style = ParagraphStyle("title_style", parent=styles["Title"],
                                  fontSize=20, spaceAfter=6,
                                  textColor=colors.HexColor("#1a1a2e"))
    h1_style    = ParagraphStyle("h1_style", parent=styles["Heading1"],
                                  fontSize=14, spaceBefore=14, spaceAfter=4,
                                  textColor=colors.HexColor("#2979ff"))
    h2_style    = ParagraphStyle("h2_style", parent=styles["Heading2"],
                                  fontSize=11, spaceBefore=8, spaceAfter=3,
                                  textColor=colors.HexColor("#555555"))
    body_style  = ParagraphStyle("body_style", parent=styles["Normal"],
                                  fontSize=9, leading=14, spaceAfter=4)
    caption_style = ParagraphStyle("caption_style", parent=styles["Normal"],
                                    fontSize=7, textColor=colors.grey,
                                    spaceAfter=6)

    def add_kv(label, value, style=body_style):
        story.append(Paragraph(f"<b>{label}:</b> {value}", style))

    def add_hr():
        story.append(HRFlowable(width="100%", thickness=0.5,
                                 color=colors.HexColor("#dddddd"), spaceAfter=6))

    def fig_to_rl_image(fig, width_cm=16, height_cm=8):
        """Convert plotly figure to ReportLab Image."""
        try:
            img_bytes = pio.to_image(fig, format="png", width=900, height=450, scale=2)
            img_buf   = BytesIO(img_bytes)
            return RLImage(img_buf, width=width_cm*cm, height=height_cm*cm)
        except Exception as e:
            return Paragraph(f"[Chart unavailable: {e}]", caption_style)

    # ── Cover ────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Stockly AI Analysis Report", title_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}", caption_style))
    story.append(Spacer(1, 0.3*cm))
    add_hr()

    # ════════════════════════════════════════════════════════
    # SECTION 1 — STOCK PREDICTION
    # ════════════════════════════════════════════════════════
    if pred_result and not pred_result.get("error"):
        story.append(Paragraph(f"1. Stock Prediction — {selected_ticker}", h1_style))

        signal_color_map = {"BUY": "#00c853", "SELL": "#ff1744", "HOLD": "#ff9100"}
        signal  = pred_result.get("signal",     "N/A")
        outlook = pred_result.get("outlook",    "N/A")
        sc      = signal_color_map.get(signal, "#555555")

        # Signal table
        data = [
            ["Signal", "Confidence", "Outlook", "Support", "Resistance"],
            [
                Paragraph(f'<font color="{sc}"><b>{signal}</b></font>', body_style),
                pred_result.get("confidence", "N/A"),
                outlook,
                f"${pred_result.get('support', 'N/A')}",
                f"${pred_result.get('resistance', 'N/A')}",
            ]
        ]
        tbl = Table(data, colWidths=[usable_w/5]*5)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#f0f4ff")),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN",       (0,0), (-1,-1), "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("<b>AI Summary</b>", h2_style))
        story.append(Paragraph(pred_result.get("summary", ""), body_style))

        # Chart
        if pred_history is not None:
            story.append(Spacer(1, 0.3*cm))
            predicted  = pred_result.get("predicted_closes", [])
            last_date  = pred_history.index[-1]
            pred_dates = [last_date + timedelta(days=i+1) for i in range(len(predicted))]
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=pred_history.tail(30).index,
                open=pred_history.tail(30)["Open"],
                high=pred_history.tail(30)["High"],
                low=pred_history.tail(30)["Low"],
                close=pred_history.tail(30)["Close"],
                name="Historical",
                increasing_line_color="#00c853",
                decreasing_line_color="#ff1744",
            ))
            if predicted:
                pred_x = [pred_history.index[-1]] + pred_dates
                pred_y = [float(pred_history["Close"].iloc[-1])] + [float(p) for p in predicted]
                fig.add_trace(go.Scatter(
                    x=pred_x, y=pred_y, mode="lines+markers",
                    name="AI Forecast",
                    line=dict(color="#2979ff", width=2, dash="dash"),
                    marker=dict(size=5),
                ))
            fig.update_layout(
                title=f"{selected_ticker} — Historical + 7-Day Forecast",
                xaxis_rangeslider_visible=False,
                template="plotly_white", height=400,
            )
            story.append(fig_to_rl_image(fig))

        add_hr()

    # ════════════════════════════════════════════════════════
    # SECTION 2 — TOP 5 TICKERS
    # ════════════════════════════════════════════════════════
    if top5_result and top5_raw:
        story.append(Paragraph("2. Top 5 Tickers Today", h1_style))
        TOP5 = ["AAPL", "MSFT", "NVDA", "TSLA", "META"]

        rows = [["Ticker", "Price", "Change %", "Signal", "Analysis"]]
        for t in TOP5:
            det     = top5_raw[t][0]
            ai_info = top5_result.get(t, {})
            signal  = ai_info.get("signal", "N/A")
            sc      = signal_color_map.get(signal, "#555555") if "signal_color_map" in dir() else "#555555"
            change  = det.get("change_pct", 0)
            rows.append([
                t,
                f"${det.get('price', 'N/A')}",
                f"{'+' if change >= 0 else ''}{change:.2f}%",
                Paragraph(f'<font color="{sc}"><b>{signal}</b></font>', body_style),
                Paragraph(ai_info.get("one_line", ""), body_style),
            ])

        tbl2 = Table(rows, colWidths=[1.5*cm, 2*cm, 2*cm, 2*cm, usable_w-7.5*cm])
        tbl2.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#f0f4ff")),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN",       (0,0), (3,0),   "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
        ]))
        story.append(tbl2)
        story.append(Spacer(1, 0.3*cm))

        # Normalized comparison chart
        colors_list = ["#2979ff", "#00c853", "#ff9100", "#ff1744", "#aa00ff"]
        fig3 = go.Figure()
        for idx, t in enumerate(TOP5):
            hist_t  = top5_raw[t][1]
            closes  = hist_t["Close"].tail(30)
            base    = float(closes.iloc[0])
            norm    = (closes / base * 100).tolist()
            fig3.add_trace(go.Scatter(
                x=closes.index.tolist(), y=norm,
                mode="lines", name=t,
                line=dict(color=colors_list[idx], width=2),
            ))
        fig3.update_layout(
            title="Top 5 — Normalized Price Performance (Last 30 Days)",
            template="plotly_white", height=380,
        )
        story.append(fig_to_rl_image(fig3))
        add_hr()

    # ════════════════════════════════════════════════════════
    # SECTION 3 — MARKET SENTIMENT
    # ════════════════════════════════════════════════════════
    if market_sentiment and not market_sentiment.get("error"):
        story.append(Paragraph("3. Market Sentiment Today", h1_style))
        ms = market_sentiment
        overall    = ms.get("overall",    "N/A")
        score      = ms.get("score",      50)
        fear_greed = ms.get("fear_greed", "N/A")

        sent_data = [
            ["Overall Sentiment", "Score", "Fear / Greed"],
            [overall, f"{score}/100", fear_greed],
        ]
        tbl3 = Table(sent_data, colWidths=[usable_w/3]*3)
        tbl3.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#f0f4ff")),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 10),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN",       (0,0), (-1,-1), "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(tbl3)
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"<b>Theme:</b> {ms.get('theme','')}", body_style))
        story.append(Paragraph(ms.get("summary", ""), body_style))
        add_hr()

    # ════════════════════════════════════════════════════════
    # SECTION 4 — PORTFOLIO HEALTH
    # ════════════════════════════════════════════════════════
    if health_result and not health_result.get("error"):
        story.append(Paragraph("4. Portfolio Health Grade", h1_style))
        r   = health_result
        sub = r.get("sub_scores", {})

        grade_data = [
            ["Grade", "Diversification", "Performance", "Risk Management"],
            [
                Paragraph(f'<font size="18"><b>{r.get("grade","N/A")}</b></font>', body_style),
                f"{sub.get('diversification','N/A')}/10",
                f"{sub.get('performance','N/A')}/10",
                f"{sub.get('risk_management','N/A')}/10",
            ]
        ]
        tbl4 = Table(grade_data, colWidths=[usable_w/4]*4)
        tbl4.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#f0f4ff")),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN",       (0,0), (-1,-1), "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(tbl4)
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("<b>Overview</b>", h2_style))
        story.append(Paragraph(r.get("overview",""), body_style))

        risk_tip_data = [["Risks", "Suggestions"]]
        risks = "\n".join([f"• {x}" for x in r.get("risks", [])])
        tips  = "\n".join([f"• {x}" for x in r.get("tips",  [])])
        risk_tip_data.append([
            Paragraph(risks.replace("\n","<br/>"), body_style),
            Paragraph(tips.replace("\n","<br/>"),  body_style),
        ])
        tbl5 = Table(risk_tip_data, colWidths=[usable_w/2, usable_w/2])
        tbl5.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#f0f4ff")),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ]))
        story.append(tbl5)
        story.append(Spacer(1, 0.3*cm))

        if r.get("verdict"):
            story.append(Paragraph(f"<b>Verdict:</b> {r['verdict']}", body_style))

        # Portfolio holdings table
        if not portfolio_df.empty:
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph("<b>Holdings</b>", h2_style))
            hold_rows = [["Asset", "Detail", "Value", "Gain/Loss", "Gain %"]]
            for _, row in portfolio_df.iterrows():
                hold_rows.append([
                    row["ASSET"],
                    row["DETAIL"],
                    f"${row['BALANCE']:.2f}",
                    f"${row['GAIN']:.2f}",
                    f"{row['GAIN_PCT']:.1f}%",
                ])
            tbl6 = Table(hold_rows, colWidths=[2*cm, 4*cm, 2.5*cm, 2.5*cm, 2*cm])
            tbl6.setStyle(TableStyle([
                ("BACKGROUND",     (0,0), (-1,0), colors.HexColor("#f0f4ff")),
                ("FONTNAME",       (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",       (0,0), (-1,-1), 8),
                ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
                ("ALIGN",          (2,0), (-1,-1), "RIGHT"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
            ]))
            story.append(tbl6)

        add_hr()

    # ── Footer ───────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "This report is generated by Stockly AI powered by Gemma 3 27B. "
        "All analysis is for informational purposes only and does not constitute financial advice.",
        caption_style
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()



def render_ai_tab(selected_ticker, details, history,
                   portfolio_df, total_invested, total_value,
                   fetch_stock_details_fn, fetch_news_fn):

    st.markdown("## AI Insights")
    st.caption("Powered by Gemma 3 27B · All analysis uses live cached data · Not financial advice")
    st.markdown("---")

    # ── Init session state keys ──────────────────────────────
    if "analysis_done"   not in st.session_state: st.session_state.analysis_done   = False
    if "pred_ticker"     not in st.session_state: st.session_state.pred_ticker      = None
    if "pred_result"     not in st.session_state: st.session_state.pred_result      = None
    if "pred_history"    not in st.session_state: st.session_state.pred_history     = None
    if "top5_raw"        not in st.session_state: st.session_state.top5_raw         = None
    if "top5_result"     not in st.session_state: st.session_state.top5_result      = None
    if "market_sentiment"not in st.session_state: st.session_state.market_sentiment = None
    if "health_result"   not in st.session_state: st.session_state.health_result    = None

    # ── Auto-update prediction when ticker changes ───────────
    # Only re-runs prediction — top5 and sentiment stay cached
    if st.session_state.analysis_done and st.session_state.pred_ticker != selected_ticker:
        with st.spinner(f"Ticker changed — updating prediction for {selected_ticker}..."):
            st.session_state.pred_result  = ai_ticker_prediction(selected_ticker, details, history)
            st.session_state.pred_ticker  = selected_ticker
            st.session_state.pred_history = history
        st.rerun()

    # ── Show button only if analysis has NOT been run yet ────
    if not st.session_state.analysis_done:
        if st.button("Run AI Analysis", key="run_all_btn", type="primary", use_container_width=True):
            with st.spinner("Step 1/3  Predicting price for " + selected_ticker + "..."):
                st.session_state.pred_result  = ai_ticker_prediction(selected_ticker, details, history)
                st.session_state.pred_ticker  = selected_ticker
                st.session_state.pred_history = history

            with st.spinner("Step 2/3  Analyzing top 5 tickers..."):
                top5_data  = {}
                top5_preds = {}
                for t in ["AAPL", "MSFT", "NVDA", "TSLA", "META"]:
                    det, hist_t = fetch_stock_details_fn(t, period="1mo")
                    top5_data[t]  = (det, hist_t)
                    top5_preds[t] = ai_ticker_prediction(t, det, hist_t)
                st.session_state.top5_raw    = top5_data
                st.session_state.top5_preds  = top5_preds
                st.session_state.top5_result = ai_top5_analysis(top5_data)

            with st.spinner("Step 3/3  Reading market sentiment..."):
                all_headlines = []
                for t in ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOG"]:
                    news = fetch_news_fn(t)
                    for item in news[:3]:
                        content = item.get("content") or {}
                        title   = content.get("title", "")
                        if title:
                            all_headlines.append(title)
                st.session_state.market_sentiment = ai_market_sentiment(all_headlines)

            st.session_state.analysis_done = True
            st.rerun()

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # SECTION 1 — STOCK PREDICTION
    # ══════════════════════════════════════════════════════════

    st.markdown("### Stock Prediction")
    st.caption(f"Selected: **{selected_ticker}** — last 30 days + 7-day AI forecast")

    if st.session_state.pred_result and not st.session_state.pred_result.get("error"):
        r       = st.session_state.pred_result
        hist    = st.session_state.pred_history
        signal  = r.get("signal",  "N/A")
        outlook = r.get("outlook", "N/A")

        signal_colors  = {"BUY": "#00c853", "SELL": "#ff1744", "HOLD": "#ff9100", "N/A": "#9e9e9e"}
        outlook_colors = {"Bullish": "#00c853", "Bearish": "#ff1744", "Neutral": "#ff9100", "N/A": "#9e9e9e"}

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            with st.container(border=True):
                st.markdown("**Signal**")
                st.markdown(
                    f"<p style='font-size:22px;font-weight:700;"
                    f"color:{signal_colors.get(signal)}'>{signal}</p>",
                    unsafe_allow_html=True)
                st.caption(f"Confidence: {r.get('confidence','N/A')}")
        with m2:
            with st.container(border=True):
                st.markdown("**Outlook**")
                st.markdown(
                    f"<p style='font-size:22px;font-weight:700;"
                    f"color:{outlook_colors.get(outlook)}'>{outlook}</p>",
                    unsafe_allow_html=True)
        with m3:
            with st.container(border=True):
                st.markdown("**Support**")
                st.markdown(
                    f"<p style='font-size:22px;font-weight:700'>${r.get('support','N/A')}</p>",
                    unsafe_allow_html=True)
        with m4:
            with st.container(border=True):
                st.markdown("**Resistance**")
                st.markdown(
                    f"<p style='font-size:22px;font-weight:700'>${r.get('resistance','N/A')}</p>",
                    unsafe_allow_html=True)

        predicted  = r.get("predicted_closes", [])
        last_date  = hist.index[-1]
        pred_dates = [last_date + timedelta(days=i + 1) for i in range(len(predicted))]

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist.tail(30).index,
            open=hist.tail(30)["Open"],
            high=hist.tail(30)["High"],
            low=hist.tail(30)["Low"],
            close=hist.tail(30)["Close"],
            name="Historical",
            increasing_line_color="#00c853",
            decreasing_line_color="#ff1744",
        ))
        if predicted:
            pred_x = [hist.index[-1]] + pred_dates
            pred_y = [float(hist["Close"].iloc[-1])] + [float(p) for p in predicted]
            fig.add_trace(go.Scatter(
                x=pred_x, y=pred_y,
                mode="lines+markers",
                name="AI Forecast",
                line=dict(color="#2979ff", width=2, dash="dash"),
                marker=dict(size=6, color="#2979ff"),
            ))
        fig.update_layout(
            title=f"{selected_ticker} — Historical + 7-Day AI Forecast",
            xaxis_title="Date", yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False,
            template="plotly_dark", height=400,
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.container(border=True):
            st.markdown("**AI Summary**")
            st.write(r.get("summary", ""))

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # SECTION 2 — TOP 5 TICKERS TODAY
    # ══════════════════════════════════════════════════════════

    st.markdown("### Top 5 Tickers Today")
    st.caption("AAPL · MSFT · NVDA · TSLA · META")

    if st.session_state.top5_result and st.session_state.top5_raw:
        ai_res   = st.session_state.top5_result
        raw_data = st.session_state.top5_raw
        signal_colors = {"BUY": "#00c853", "SELL": "#ff1744", "HOLD": "#ff9100", "N/A": "#9e9e9e"}
        TOP5 = ["AAPL", "MSFT", "NVDA", "TSLA", "META"]

        # ── 5 ticker cards ───────────────────────────────────
        cols = st.columns(5)
        for i, t in enumerate(TOP5):
            det      = raw_data[t][0]
            ai_info  = ai_res.get(t, {})
            signal   = ai_info.get("signal", "N/A")
            one_line = ai_info.get("one_line", "")
            price    = det.get("price", "N/A")
            change   = det.get("change_pct", 0)
            chg_color = "#00c853" if change >= 0 else "#ff1744"
            chg_sign  = "+" if change >= 0 else ""

            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{t}**")
                    st.markdown(
                        f"<p style='font-size:18px;font-weight:600;margin:2px 0'>${price}</p>"
                        f"<p style='color:{chg_color};margin:0;font-size:13px'>{chg_sign}{change:.2f}%</p>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<span style='background:{signal_colors.get(signal)};color:white;"
                        f"padding:2px 10px;border-radius:4px;font-size:12px;font-weight:600'>"
                        f"{signal}</span>",
                        unsafe_allow_html=True,
                    )
                    st.caption(one_line)

        # ── Normalized historical price comparison (last 30 days) ──
        colors_list = ["#2979ff", "#00c853", "#ff9100", "#ff1744", "#aa00ff"]
        fig2 = go.Figure()

        for idx, t in enumerate(TOP5):
            hist_t     = raw_data[t][1]
            closes     = hist_t["Close"].tail(30)
            base       = float(closes.iloc[0])
            norm       = (closes / base * 100).tolist()
            fig2.add_trace(go.Scatter(
                x=closes.index.tolist(),
                y=norm,
                mode="lines",
                name=t,
                line=dict(color=colors_list[idx], width=2),
            ))

        fig2.update_layout(
            title="Top 5 — Normalized Price Performance (Last 30 Days, Base=100)",
            xaxis_title="Date",
            yaxis_title="Normalized Price",
            template="plotly_dark",
            height=380,
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # SECTION 3 — MARKET SENTIMENT TODAY
    # ══════════════════════════════════════════════════════════

    st.markdown("### Market Sentiment Today")
    st.caption("Scored from latest news across AAPL · MSFT · NVDA · TSLA · META · AMZN · GOOG")

    if st.session_state.market_sentiment and not st.session_state.market_sentiment.get("error"):
        ms         = st.session_state.market_sentiment
        overall    = ms.get("overall",    "N/A")
        score      = ms.get("score",      50)
        fear_greed = ms.get("fear_greed", "N/A")
        overall_colors = {"Bullish": "#00c853", "Bearish": "#ff1744", "Neutral": "#ff9100", "N/A": "#9e9e9e"}
        fg_colors      = {"Greed":   "#00c853", "Fear":    "#ff1744", "Neutral": "#ff9100", "N/A": "#9e9e9e"}

        s1, s2, s3 = st.columns(3)
        with s1:
            with st.container(border=True):
                st.markdown("**Overall Sentiment**")
                st.markdown(
                    f"<p style='font-size:26px;font-weight:700;"
                    f"color:{overall_colors.get(overall)}'>{overall}</p>",
                    unsafe_allow_html=True)
        with s2:
            with st.container(border=True):
                st.markdown("**Sentiment Score**")
                st.markdown(f"<p style='font-size:26px;font-weight:700'>{score}/100</p>",
                            unsafe_allow_html=True)
                st.progress(score / 100)
        with s3:
            with st.container(border=True):
                st.markdown("**Fear / Greed**")
                st.markdown(
                    f"<p style='font-size:26px;font-weight:700;"
                    f"color:{fg_colors.get(fear_greed)}'>{fear_greed}</p>",
                    unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(f"**Theme:** {ms.get('theme','')}")
            st.write(ms.get("summary", ""))

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # SECTION 4 — PORTFOLIO ANALYSIS
    # ══════════════════════════════════════════════════════════

    st.markdown("### Portfolio Analysis")
    st.caption("Grade and breakdown based on your uploaded holdings")

    if not st.session_state.health_result:
        if st.button("Analyze My Portfolio", key="port_btn", type="primary"):
            if not portfolio_df.empty:
                with st.spinner("Grading your portfolio..."):
                    st.session_state.health_result = ai_portfolio_health(
                        portfolio_df, total_invested, total_value
                    )
                st.rerun()
            else:
                st.warning("Upload a CSV in the Portfolio tab first.")

    if st.session_state.health_result and not st.session_state.health_result.get("error"):
        r     = st.session_state.health_result
        grade = r.get("grade", "N/A")
        sub   = r.get("sub_scores", {})
        grade_colors = {
            "A": "#00c853", "B": "#7cb342", "C": "#ffa726",
            "D": "#ef5350", "F": "#b71c1c", "N/A": "#9e9e9e",
        }
        color = grade_colors.get(grade, "#9e9e9e")

        g_col, sc1, sc2, sc3 = st.columns([1, 1, 1, 1])
        with g_col:
            with st.container(border=True):
                st.markdown("**Portfolio Grade**")
                st.markdown(
                    f"<p style='font-size:64px;font-weight:800;color:{color};"
                    f"text-align:center;margin:0'>{grade}</p>",
                    unsafe_allow_html=True)
        with sc1:
            with st.container(border=True):
                st.markdown("**Diversification**")
                st.markdown(
                    f"<p style='font-size:32px;font-weight:700'>"
                    f"{sub.get('diversification','N/A')}"
                    f"<span style='font-size:14px'>/10</span></p>",
                    unsafe_allow_html=True)
        with sc2:
            with st.container(border=True):
                st.markdown("**Performance**")
                st.markdown(
                    f"<p style='font-size:32px;font-weight:700'>"
                    f"{sub.get('performance','N/A')}"
                    f"<span style='font-size:14px'>/10</span></p>",
                    unsafe_allow_html=True)
        with sc3:
            with st.container(border=True):
                st.markdown("**Risk Management**")
                st.markdown(
                    f"<p style='font-size:32px;font-weight:700'>"
                    f"{sub.get('risk_management','N/A')}"
                    f"<span style='font-size:14px'>/10</span></p>",
                    unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**Overview**")
            st.write(r.get("overview", ""))

        risk_col, tip_col = st.columns(2)
        with risk_col:
            with st.container(border=True):
                st.markdown("**Risks**")
                for risk in r.get("risks", []):
                    st.markdown(f"- {risk}")
        with tip_col:
            with st.container(border=True):
                st.markdown("**Suggestions**")
                for tip in r.get("tips", []):
                    st.markdown(f"- {tip}")

        if r.get("verdict"):
            st.info(r["verdict"])

        st.caption("Not financial advice.")

    st.markdown("---")

    # ── Download PDF ─────────────────────────────────────────
    if st.session_state.analysis_done:
        if st.button("Generate PDF Report", key="pdf_btn"):
            with st.spinner("Building PDF..."):
                pdf_bytes = generate_pdf_report(
                    selected_ticker=selected_ticker,
                    pred_result=st.session_state.get("pred_result"),
                    pred_history=st.session_state.get("pred_history"),
                    top5_result=st.session_state.get("top5_result"),
                    top5_raw=st.session_state.get("top5_raw"),
                    market_sentiment=st.session_state.get("market_sentiment"),
                    health_result=st.session_state.get("health_result"),
                    portfolio_df=portfolio_df,
                )
            st.download_button(
                label="Download Analysis PDF",
                data=pdf_bytes,
                file_name=f"stockly_ai_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
