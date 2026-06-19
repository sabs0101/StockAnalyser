# 📈 StockSage India

AI-powered Indian stock market analyser — live NSE prices, RSI/SMA indicators, news sentiment scoring, and human-like AI recommendations.

---

## Prerequisites

Before running this project, make sure the following are installed:

| Requirement | Version | Download |
|-------------|---------|----------|
| **Python** | 3.9 or higher | https://www.python.org/downloads/ |
| **pip** | (comes with Python) | — |

> ⚠️ During Python installation on Windows, tick **"Add Python to PATH"**.

---

## Setup Instructions

### Step 1 — Clone / Copy the project folder

Make sure your folder structure looks like this:

```
stockanalyser/
├── backend/
│   ├── app.py
│   └── analyser.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── requirements.txt
└── README.md
```

### Step 2 — Install Python dependencies

Open a terminal (Command Prompt or PowerShell) inside the `stockanalyser` folder and run:

```bash
pip install -r requirements.txt
```

This installs:
- **flask** — web server / API
- **flask-cors** — allows browser to call the API
- **yfinance** — fetches live NSE stock prices from Yahoo Finance
- **pandas** — data processing for price history
- **requests** — HTTP calls to NewsAPI
- **textblob** — sentiment analysis on news headlines
- **nltk** — natural language toolkit (used by textblob internally)

### Step 3 — Download NLTK data (one-time)

TextBlob needs a small language dataset on first use. Run once:

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('brown')"
```

### Step 4 — Start the backend server

```bash
cd backend
python app.py
```

You should see:

```
StockSage India running at: http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

### Step 5 — Open the app

Open your browser and go to:

```
http://127.0.0.1:5000
```

> Keep the terminal open while using the app — closing it stops the server.

---

## API Keys (already included)

The project uses two free-tier API keys that are already configured in `backend/analyser.py`:

| Service | Usage | Key |
|---------|-------|-----|
| **Alpha Vantage** | (backup, not primary) | `SQ8428106D4FY5CL` |
| **NewsAPI** | Fetches stock-specific news | `8be9809cedd24f03a5c65fb1bdf268a1` |

> ⚠️ NewsAPI free tier allows **100 requests/day**. If news stops working, the free limit may be  reached. Get a new free key at https://newsapi.org/

---

## How to Use

1. Click **"Recommend Stocks"** on the splash screen
2. Wait ~20–30 seconds for 12 NSE stocks to load (sorted LOW → MEDIUM → HIGH risk)
3. Click any card for a **deep AI analysis** including:
   - Price history chart (1M / 3M / 6M / 1Y / 2Y)
   - RSI gauge, SMA, sentiment score
   - Human-like AI analyst commentary
   - Recent news with **positive / negative / neutral** sentiment indicators
4. Or use the **search bar** to analyse any NSE stock (e.g. `TATASTEEL`, `BAJAJFINSV`, `NIFTY50`)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
| Port 5000 already in use | Kill old process: `netstat -ano \| findstr :5000`, then `taskkill /PID <id> /F` |
| News not loading | NewsAPI daily limit may be reached (100 req/day on free tier) |
| Stock not found | Add `.NS` suffix — e.g. `TATASTEEL.NS` |
| `python` not recognized | Reinstall Python and tick "Add Python to PATH" |
