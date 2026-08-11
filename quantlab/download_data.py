# download_data.py — pull daily history for the universe, store as Parquet
import pathlib
import yfinance as yf

UNIVERSE = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","AVGO","TSLA","LLY","JPM",
    "V","XOM","UNH","MA","COST","HD","PG","JNJ","ABBV","WMT",
    "NFLX","CRM","BAC","ORCL","MRK","KO","AMD","PEP","CVX","ADBE",
    "TMO","CSCO","MU","QCOM","TXN","INTC","IBM","GE","CAT","LIN",
]  # ~40 liquid US large caps — edit freely, but keep them liquid

OUT = pathlib.Path("data"); OUT.mkdir(exist_ok=True)
px = yf.download(UNIVERSE, start="2010-01-01", auto_adjust=True)["Close"]
px.to_parquet(OUT / "close.parquet")
print(f"Saved {px.shape[1]} symbols x {px.shape[0]} days -> data/close.parquet")
