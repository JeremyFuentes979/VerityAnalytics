"""Optional external reference data (FX rates, benchmarks) via yfinance.

yfinance is imported lazily so the rest of the pipeline works without it.
"""

import json
import math
import sys
from datetime import datetime, timedelta


def _yf():
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed. Run: pip install yfinance") from exc
    return yf


def clean_value(val):
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def get_fx_rate(base_currency, target_currency, date=None):
    symbol = f"{base_currency}{target_currency}=X"
    ticker = _yf().Ticker(symbol)

    if date:
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
    else:
        hist = ticker.history(period="1d")

    if hist.empty:
        return {"error": f"No data found for {symbol}"}
    return {
        "symbol": symbol,
        "rate": clean_value(float(hist["Close"].iloc[-1])),
        "date": hist.index[-1].strftime("%Y-%m-%d"),
    }


def get_benchmark(symbol, period="1mo"):
    hist = _yf().Ticker(symbol).history(period=period)
    if hist.empty:
        return {"error": f"No data found for {symbol}"}
    data = [
        {"date": index.strftime("%Y-%m-%d"), "close": clean_value(float(row["Close"])), "volume": int(row["Volume"])}
        for index, row in hist.iterrows()
    ]
    return {"symbol": symbol, "data": data}


def main():
    if len(sys.argv) < 2:
        print("Usage: python reference_data.py <type> <params...>")
        print("Types: fx <base> <target> [date], benchmark <symbol> [period]")
        sys.exit(1)

    rtype = sys.argv[1]
    if rtype == "fx":
        result = get_fx_rate(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif rtype == "benchmark":
        result = get_benchmark(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "1mo")
    else:
        result = {"error": f"Unknown type: {rtype}"}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
