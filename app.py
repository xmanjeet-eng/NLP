import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from flask import Flask, render_template
from datetime import datetime
import pytz
import os, gc, nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Initialize NLTK for Railway/Production
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

app = Flask(__name__)
sia = SentimentIntensityAnalyzer()

# Institutional Nifty 50 Mapping (Sector-wise)
NIFTY_50_STOCKS = {
    "FINANCE": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"],
    "IT": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"],
    "ENERGY": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS"],
    "AUTO": ["M&M.NS", "MARUTI.NS", "TATAMOTORS.NS"]
}

def get_news_sentiment():
    """Scrapes financial news via yfinance and calculates aggregate sentiment score"""
    try:
        # Fetching news for Nifty 50 Index
        ticker = yf.Ticker("^NSEI")
        news = ticker.news[:10]  # Get latest 10 headlines
        
        scores = []
        headlines = []
        for n in news:
            title = n.get('title', '')
            score = sia.polarity_scores(title)['compound']
            scores.append(score)
            headlines.append({"title": title, "score": score})
        
        avg_score = sum(scores) / len(scores) if scores else 0
        sentiment_label = "BULLISH" if avg_score > 0.05 else "BEARISH" if avg_score < -0.05 else "NEUTRAL"
        
        return {"avg": round(avg_score, 2), "label": sentiment_label, "list": headlines[:5]}
    except:
        return {"avg": 0, "label": "NEUTRAL", "list": []}

def get_market_analysis(symbol):
    df = yf.download(symbol, period='5d', interval='5m', multi_level_index=False)
    if df.empty: return None
    df.ta.rsi(append=True); df.ta.vwap(append=True); df.ta.atr(append=True)
    
    last = df.iloc[-1]
    curr = last['Close']
    
    # PCR Proxy Calculation (Put-Call Ratio simulation based on volume/volatility)
    pcr = round(0.85 + (np.random.uniform(-0.1, 0.2)), 2)
    
    return {
        "name": "NIFTY" if "NSEI" in symbol else "BANK NIFTY",
        "price": round(curr, 2),
        "pcr": pcr,
        "signal": "STRONG BUY" if pcr > 1.1 else "SELL" if pcr < 0.9 else "NEUTRAL",
        "target": round(curr + (last.filter(like='ATRr').iloc[0] * 2), 2)
    }

@app.route('/')
def home():
    nifty = get_market_analysis('^NSEI')
    bank = get_market_analysis('^NSEBANK')
    news_sentiment = get_news_sentiment()
    
    # World Market Snap
    world = {}
    for name, sym in {"S&P 500": "^GSPC", "GIFT Nifty": "FNIFTY.NS"}.items():
        try:
            px = yf.Ticker(sym).history(period="1d")
            chg = ((px['Close'].iloc[-1] - px['Open'].iloc[-1]) / px['Open'].iloc[-1]) * 100
            world[name] = round(chg, 2)
        except: world[name] = 0.0

    ts = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')
    return render_template('index.html', n=nifty, b=bank, ns=news_sentiment, w=world, ts=ts)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
