import math
from datetime import datetime
import requests
import yfinance as yf
import concurrent.futures
from textblob import TextBlob

NEWS_API_KEY = "8be9809cedd24f03a5c65fb1bdf268a1"

INDIAN_STOCKS = [
    {"symbol": "RELIANCE.NS",  "name": "Reliance Industries",        "sector": "Energy & Retail"},
    {"symbol": "TCS.NS",       "name": "Tata Consultancy Services",  "sector": "Information Technology"},
    {"symbol": "HDFCBANK.NS",  "name": "HDFC Bank",                  "sector": "Banking"},
    {"symbol": "INFY.NS",      "name": "Infosys",                    "sector": "Information Technology"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank",                 "sector": "Banking"},
    {"symbol": "SBIN.NS",      "name": "State Bank of India",        "sector": "Banking"},
    {"symbol": "WIPRO.NS",     "name": "Wipro",                      "sector": "Information Technology"},
    {"symbol": "BAJFINANCE.NS","name": "Bajaj Finance",              "sector": "Finance"},
    {"symbol": "MARUTI.NS",    "name": "Maruti Suzuki",              "sector": "Automobile"},
    {"symbol": "TATAMOTORS.NS","name": "Tata Motors",                "sector": "Automobile"},
    {"symbol": "HCLTECH.NS",   "name": "HCL Technologies",           "sector": "Information Technology"},
    {"symbol": "ADANIENT.NS",  "name": "Adani Enterprises",          "sector": "Diversified"},
]


def safe_round(value, decimals=2):
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


def compute_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs    = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def get_news(company_name, ticker_symbol):
    """
    Fetch news articles where the company name appears IN THE HEADLINE (qInTitle).
    Falls back to a body-search sorted by relevancy if fewer than 3 results.
    """
    # Build a concise title query — use ticker for brevity (e.g. 'WIPRO', 'TCS')
    title_query = ticker_symbol  # must appear in article title
    body_query  = f'"{company_name}" OR "{ticker_symbol}"'

    try:
        # Primary: must appear in headline
        url = (
            f"https://newsapi.org/v2/everything"
            f"?qInTitle={requests.utils.quote(title_query)}"
            f"&language=en&sortBy=publishedAt"
            f"&pageSize=15&apiKey={NEWS_API_KEY}"
        )
        articles = requests.get(url, timeout=10).json().get("articles", [])

        if len(articles) < 3:
            # Fallback: company name anywhere in body, sorted by relevancy
            url2 = (
                f"https://newsapi.org/v2/everything"
                f"?q={requests.utils.quote(body_query)}"
                f"&language=en&sortBy=relevancy"
                f"&pageSize=10&apiKey={NEWS_API_KEY}"
            )
            articles = requests.get(url2, timeout=10).json().get("articles", [])

        return articles
    except Exception:
        return []


def score_article(article):
    """Return article dict enriched with per-article sentiment label and score."""
    text  = (article.get("title") or "") + " " + (article.get("description") or "")
    score = TextBlob(text).sentiment.polarity
    if score > 0.1:    label = "positive"
    elif score < -0.1: label = "negative"
    else:              label = "neutral"
    return {
        "title":           article.get("title"),
        "url":             article.get("url"),
        "source":          (article.get("source") or {}).get("name"),
        "sentiment_score": safe_round(score),
        "sentiment_label": label,
    }


def analyze_sentiment(articles):
    if not articles:
        return 0.0
    scores = [
        TextBlob((a.get("title") or "") + " " + (a.get("description") or "")).sentiment.polarity
        for a in articles[:10]
    ]
    return sum(scores) / len(scores)


def get_risk(rsi):
    if rsi is None:
        return "UNKNOWN"
    if rsi > 70 or rsi < 30:
        return "HIGH"
    if 45 < rsi < 55:
        return "LOW"
    return "MEDIUM"


def get_recommendation(rsi, sentiment=0.0):
    """Tiered logic: RSI is the primary signal; sentiment is a secondary tiebreaker."""
    if rsi is None:
        return "HOLD"
    s = sentiment or 0.0  # treat None as neutral

    # Strong RSI signals — act regardless of sentiment
    if rsi <= 25:  return "BUY"    # deeply oversold
    if rsi >= 75:  return "SELL"   # deeply overbought

    # Moderate oversold/overbought: sentiment as a soft tiebreaker
    if rsi < 35:   return "BUY"  if s >= 0   else "HOLD"
    if rsi > 65:   return "SELL" if s <= 0   else "HOLD"

    # Mid-RSI zone: only signal if sentiment gives a meaningful push
    if 35 <= rsi < 45:  return "BUY"  if s > 0.05  else "HOLD"
    if 55 < rsi <= 65:  return "SELL" if s < -0.05 else "HOLD"

    return "HOLD"  # truly neutral zone (45–55 RSI, no clear sentiment)


def generate_human_analysis(name, short_sym, current_price, prev_close,
                             rsi, sma, sentiment, recommendation, risk, sector):
    paras = []
    change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
    direction  = "up" if change_pct >= 0 else "down"

    paras.append(
        f"Let me walk you through my analysis of {name} ({short_sym}). "
        f"The stock is currently trading at \u20b9{current_price:,.1f}, "
        f"{direction} {abs(change_pct):.2f}% from yesterday\u2019s close."
    )

    if sma is not None:
        pct_vs_sma = ((current_price - sma) / sma * 100)
        if current_price > sma * 1.05:
            paras.append(
                f"At \u20b9{current_price:,.1f}, the stock is trading {pct_vs_sma:.1f}% above its 14-day SMA of "
                f"\u20b9{sma:,.1f}. This signals strong short-term momentum \u2014 buyers are clearly in control. "
                f"However, when a stock runs far above its moving average it can pull back to 'mean-revert', "
                f"so new investors should be cautious about chasing at elevated levels."
            )
        elif current_price < sma * 0.95:
            paras.append(
                f"The stock is trading {abs(pct_vs_sma):.1f}% below its 14-day SMA of \u20b9{sma:,.1f}, "
                f"indicating recent selling pressure. For long-term investors dips in fundamentally strong "
                f"companies can offer attractive entries \u2014 but verify whether the weakness is temporary "
                f"or signals a deeper underlying issue."
            )
        else:
            paras.append(
                f"The stock is trading near its 14-day SMA of \u20b9{sma:,.1f}, indicating a consolidation phase. "
                f"Neither buyers nor sellers have a decisive edge currently. "
                f"This equilibrium often precedes a significant move in either direction."
            )

    if rsi is not None:
        if rsi < 30:
            paras.append(
                f"RSI is at {rsi:.1f} \u2014 firmly in oversold territory (below 30). "
                f"This suggests the stock may have been sold off more aggressively than its fundamentals justify. "
                f"Quality stocks hitting oversold levels often attract value buyers and can stage sharp recoveries. "
                f"That said, oversold does not automatically mean buy \u2014 verify no major negative catalyst exists."
            )
        elif rsi > 70:
            paras.append(
                f"RSI is at {rsi:.1f} \u2014 in overbought territory (above 70). "
                f"The recent rally has been impressive, but the stock may be overheating. "
                f"Existing holders might consider partially booking profits. "
                f"New investors may get a better entry by waiting for RSI to cool toward the 50\u201355 range."
            )
        elif rsi >= 55:
            paras.append(
                f"RSI at {rsi:.1f} reflects healthy bullish momentum without being overbought \u2014 "
                f"often called the sweet spot. Buyers are in charge, there\u2019s still room to run, "
                f"and the risk of an immediate reversal is moderate."
            )
        elif rsi <= 45:
            paras.append(
                f"With RSI at {rsi:.1f}, sellers have had a slight edge recently, though the stock isn\u2019t "
                f"in crisis. Watch for RSI to stabilize and curl upward before committing fresh capital."
            )
        else:
            paras.append(
                f"RSI at a neutral {rsi:.1f} shows the stock is balanced between buyers and sellers \u2014 "
                f"a relatively comfortable zone for a measured entry into {name}."
            )

    if sentiment is not None:
        if sentiment > 0.15:
            paras.append(
                f"News sentiment is notably positive (score: {sentiment:.2f}). "
                f"The media and analyst narrative around {name} is constructive, which can attract "
                f"retail and institutional interest and act as a price tailwind."
            )
        elif sentiment > 0.05:
            paras.append(
                f"News sentiment is mildly positive ({sentiment:.2f}) \u2014 "
                f"coverage is leaning favorable, a gentle supporting factor."
            )
        elif sentiment < -0.1:
            paras.append(
                f"News sentiment is negative ({sentiment:.2f}). There\u2019s unfavorable coverage around "
                f"{name} currently. Scan the headlines to understand if a specific fundamental concern is being flagged."
            )
        else:
            paras.append(
                f"News sentiment is broadly neutral ({sentiment:.2f}) \u2014 "
                f"no significant positive or negative narratives in the current news cycle."
            )

    sector_comments = {
        "Information Technology": (
            f"As part of India\u2019s IT sector, {name} benefits from the country\u2019s strong digital "
            f"export story. Key metrics: deal wins, attrition rates, and the USD/INR rate \u2014 "
            f"since most revenues come in dollars."
        ),
        "Banking": (
            f"As a banking stock, {name} is tied to India\u2019s credit cycle. "
            f"Monitor NPA ratios, credit growth, and the RBI\u2019s rate stance. "
            f"A rate-cut cycle typically boosts NIMs (net interest margins)."
        ),
        "Energy & Retail": (
            f"{name} is one of India\u2019s most diversified conglomerates \u2014 its O2C, "
            f"Jio telecom, and retail arms each drive value. "
            f"Often seen as a proxy for India\u2019s consumption and digital growth story."
        ),
        "Finance": (
            f"As an NBFC, {name} is sensitive to interest rate cycles and credit quality. "
            f"Watch AUM growth, NPA trends, and RBI regulatory actions."
        ),
        "Automobile": (
            f"Auto stocks like {name} follow domestic demand, rural sentiment, and steel costs. "
            f"Monthly sales volumes are the most critical near-term indicator. "
            f"The EV transition is a long-term theme worth monitoring."
        ),
        "Diversified": (
            f"{name} spans multiple business verticals, providing resilience. "
            f"Stock performance can swing on any one subsidiary\u2019s news \u2014 "
            f"watch group-level debt and EBITDA trends."
        ),
    }
    if sector in sector_comments:
        paras.append(sector_comments[sector])

    if recommendation == "BUY":
        paras.append(
            f"My verdict: BUY. Oversold technicals combined with positive sentiment create a "
            f"favorable risk-reward setup for {name}. Accumulate in 2-3 tranches rather than "
            f"going all-in, especially if broader markets are volatile."
        )
    elif recommendation == "SELL":
        paras.append(
            f"My verdict: SELL / Reduce. Overbought technicals with negative sentiment is not "
            f"an ideal combination. If sitting on profits, locking in gains is prudent. "
            f"Re-enter after RSI cools and sentiment turns neutral."
        )
    else:
        paras.append(
            f"My verdict: HOLD. No compelling trigger to buy or sell {name} right now. "
            f"Existing investors should stay put. New investors may wait for a clearer "
            f"directional signal \u2014 a better RSI setup or a meaningful price pullback."
        )

    return paras


def analyze_stock(symbol, with_news=True, period="2y"):
    stock_meta = next((s for s in INDIAN_STOCKS if s["symbol"].upper() == symbol.upper()), None)
    short_sym  = symbol.replace(".NS", "").replace(".BSE", "").upper()
    name       = stock_meta["name"]   if stock_meta else short_sym
    sector     = stock_meta["sector"] if stock_meta else "General"

    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period=period)
    except Exception as e:
        return {"error": f"Failed to fetch data: {e}"}

    if hist is None or hist.empty:
        return {"error": f"No data for {symbol}. Try a valid NSE ticker like RELIANCE.NS"}

    close         = hist["Close"]
    current_price = float(close.iloc[-1])
    prev_close    = float(close.iloc[-2]) if len(close) > 1 else current_price
    change_pct    = safe_round((current_price - prev_close) / prev_close * 100)
    rsi_series    = compute_rsi(close)
    rsi           = safe_round(rsi_series.iloc[-1])
    sma           = safe_round(close.rolling(14).mean().iloc[-1], 1)

    # Chart data: date strings + close prices
    chart_dates  = [d.strftime("%Y-%m-%d") for d in hist.index.to_list()]
    chart_prices = [safe_round(float(p), 2) for p in hist["Close"].to_list()]

    articles  = []
    sentiment = 0.0
    if with_news:
        articles  = get_news(name, short_sym)
        sentiment = analyze_sentiment(articles)

    risk           = get_risk(rsi)
    recommendation = get_recommendation(rsi, safe_round(sentiment))

    human_analysis = generate_human_analysis(
        name, short_sym, current_price, prev_close,
        rsi, sma, safe_round(sentiment), recommendation, risk, sector
    ) if with_news else []

    return {
        "symbol":         short_sym,
        "full_symbol":    symbol,
        "name":           name,
        "sector":         sector,
        "current_price":  safe_round(current_price, 1),
        "change_pct":     change_pct,
        "rsi":            rsi,
        "sma":            sma,
        "sentiment":      safe_round(sentiment),
        "recommendation": recommendation,
        "risk":           risk,
        "human_analysis": human_analysis,
        "chart_data": {"dates": chart_dates, "prices": chart_prices},
        "news": [score_article(a) for a in articles[:5]],
    }


def get_recommendations():
    results = []

    def quick_analyze(stock):
        return analyze_stock(stock["symbol"], with_news=False, period="3mo")

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futs = {executor.submit(quick_analyze, s): s for s in INDIAN_STOCKS}
        for fut in concurrent.futures.as_completed(futs):
            result = fut.result()
            if "error" not in result:
                results.append(result)

    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "UNKNOWN": 3}
    results.sort(key=lambda x: risk_order.get(x.get("risk", "UNKNOWN"), 3))
    return results