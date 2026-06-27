import yfinance as yf
import json
import sys
import os
import math
from datetime import datetime, timedelta

def clean_value(val):
    if isinstance(val, float) and math.isnan(val):
        return None
    return val

def get_fx_rate(base_currency, target_currency, date=None):
    symbol = f"{base_currency}{target_currency}=X"
    ticker = yf.Ticker(symbol)
    
    if date:
        # Get history for that date
        end_date = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
        start_date = datetime.strptime(date, "%Y-%m-%d")
        hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
    else:
        hist = ticker.history(period="1d")
    
    if not hist.empty:
        rate = hist['Close'].iloc[-1]
        return {
            "symbol": symbol,
            "rate": clean_value(float(rate)),
            "date": hist.index[-1].strftime("%Y-%m-%d")
        }
    else:
        return {"error": f"No data found for {symbol}"}

def get_benchmark(symbol, period="1mo"):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    
    if not hist.empty:
        data = []
        for index, row in hist.iterrows():
            data.append({
                "date": index.strftime("%Y-%m-%d"),
                "close": clean_value(float(row['Close'])),
                "volume": int(row['Volume'])
            })
        return {
            "symbol": symbol,
            "data": data
        }
    else:
        return {"error": f"No data found for {symbol}"}

def main():
    if len(sys.argv) < 2:
        print("Usage: python reference_data.py <type> <params...>")
        print("Types: fx <base> <target> [date], benchmark <symbol> [period]")
        sys.exit(1)

    rtype = sys.argv[1]
    
    if rtype == "fx":
        base = sys.argv[2]
        target = sys.argv[3]
        date = sys.argv[4] if len(sys.argv) > 4 else None
        result = get_fx_rate(base, target, date)
    elif rtype == "benchmark":
        symbol = sys.argv[2]
        period = sys.argv[3] if len(sys.argv) > 3 else "1mo"
        result = get_benchmark(symbol, period)
    else:
        result = {"error": f"Unknown type: {rtype}"}

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
