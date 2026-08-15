# momentum_backtest.py — 12-1 cross-sectional momentum, top 5, regime filter
import pandas as pd
import yfinance as yf
import quantstats as qs

px  = pd.read_parquet("data/close.parquet")                     # daily adjusted closes
spx = yf.download("^GSPC", start="2010-01-01", auto_adjust=True)["Close"].squeeze()

TOP_N, COST = 5, 0.0010          # 0.10% each way for commission+slippage — deliberately pessimistic
LOOKBACK, SKIP = 12, 1           # the classic "12-1" momentum definition

m_px, m_spx = px.resample("ME").last(), spx.resample("ME").last()
mom       = m_px.pct_change(LOOKBACK - SKIP).shift(SKIP)        # 12-1 momentum, known at month-end
regime_ok = m_spx > m_spx.rolling(10).mean()                    # 10-month moving-average filter

# 1) Month-end target weights: equal-weight the top N, or all-cash in a downtrend
w = pd.DataFrame(0.0, index=m_px.index, columns=m_px.columns)
for t in m_px.index:
    if bool(regime_ok.get(t, False)):
        winners = mom.loc[t].dropna().nlargest(TOP_N).index
        w.loc[t, winners] = 1.0 / TOP_N

# 2) Monthly decisions -> daily positions, held from the NEXT trading day (no lookahead)
w_daily = w.reindex(px.index, method="ffill").shift(1).fillna(0.0)

# 3) Daily returns minus costs charged whenever positions change
gross = (w_daily * px.pct_change()).sum(axis=1)
costs = w_daily.diff().abs().sum(axis=1) * COST
strat = (gross - costs).loc["2011":]                            # drop the warm-up year

qs.reports.html(strat, benchmark="^GSPC", output="momentum_report.html",
                title="12-1 momentum, top 5, regime filter")
print("Open momentum_report.html in your browser.")
