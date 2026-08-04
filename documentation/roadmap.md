# Build Your Own Quant Trading System
### A DIY roadmap: from zero to a live, hedge-fund-style pipeline on IBKR

This guide is written for you specifically: a software engineer on Windows, an active Interactive Brokers trader with real stocks-and-options experience, but new to *quantitative* trading. It assumes evenings-and-weekends pacing. Every command is PowerShell. Every piece of jargon is defined the first time it appears (and again in the Glossary at the end).

**What you'll have at the end:** a working pipeline that downloads and stores market data, backtests strategies the way funds do (a **backtest** = replaying your trading rules against historical data to see how they would have performed), runs them against an IBKR paper account, and finally trades a small live allocation with hard-coded risk limits — while feeding a journal you can use to refine your discretionary trading.

---

## The one-page summary

| Phase | What you build | Rough time | Milestone |
|---|---|---|---|
| 0 | Working Python quant workstation | one evening | A chart renders from code you ran |
| 1 | Local data foundation | one weekend | Clean 15-year price history stored on disk |
| 2 | **The prototype**: first honest backtest | 2–3 weekends | A performance report for a rules-based strategy, with costs, that survived out-of-sample testing |
| 3 | Institutional engine (LEAN) | 2–4 weekends | Same strategy running in the engine hedge funds actually use |
| 4 | Paper trading on IBKR | 1 weekend setup, then 4–8 weeks running | System places simulated orders unattended |
| 5 | Live, small, with a risk module | ongoing | Small real allocation, kill-switches, monitoring |
| 6 | Options & other derivatives | after 5 is stable | Systematic options strategies on top of the same pipeline |

The end of Phase 2 is the prototype you asked for. Phases 3–5 industrialise it. Phase 6 extends it to derivatives.

---

## Part 1 — The blueprint: what's actually inside a hedge-fund system

Strip away the marketing and every systematic fund is six boxes:

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────────┐   ┌───────────┐   ┌────────────┐
│  1 DATA  │ → │ 2 RESEARCH│ → │ 3 SIGNALS │ → │ 4 PORTFOLIO │ → │ 5 EXECUTION│ → │ 6 MONITORING│
│ ingest,  │   │ notebooks,│   │ the rules │   │  & RISK     │   │ orders to │   │ logs, alerts│
│ clean,   │   │ backtests │   │ that say  │   │ sizing,     │   │ the broker│   │ attribution,│
│ store    │   │           │   │ buy/sell  │   │ limits      │   │ (IBKR)    │   │ journal     │
└──────────┘   └──────────┘   └──────────┘   └─────────────┘   └───────────┘   └────────────┘
```

1. **Data** — historical and live prices (and later fundamentals, options chains) pulled in, cleaned, and stored so research is reproducible.
2. **Research** — where you build the mathematical and statistical models: notebooks, factor studies, backtests.
3. **Signals / strategy** — the codified rules a model produces ("hold the 5 strongest stocks of the last 12 months unless the market is in a downtrend").
4. **Portfolio construction & risk** — turning signals into position sizes, with limits: max per position, max exposure, kill-switches.
5. **Execution** — translating target positions into broker orders. For you: IBKR's API.
6. **Monitoring** — logging, alerts, performance attribution. The read-only trade journal you've already scoped over your IBKR history lives here — it becomes the attribution layer that compares the system's book against your discretionary book, and it doubles as a clean audit trail.

What actual funds have that you won't: multi-vendor data budgets, redundant infrastructure, and headcount. What they don't have that you do: no investors to answer to, no capacity constraints, and the freedom to trade slowly. The *architecture* above is fully reproducible at home, and that's what this roadmap builds.

---

## Part 2 — The stack: open-source pieces so you don't start from scratch

**Language: Python.** Not because TypeScript or Java couldn't do it, but because ~95% of open-source quant tooling, every framework below, and every book worth reading is Python. With your background the switch is a weekend, not a project. (Your TS skills stay useful later for dashboards.)

| Layer | Tool | What it is |
|---|---|---|
| Research backtests | **vectorbt** | Very fast "vectorized" backtesting library — tests rules across whole price histories in milliseconds. Ideal for idea iteration. |
| Performance reports | **quantstats** | One command turns a return series into a full HTML "tearsheet" (fund-style performance report: returns, drawdowns, risk stats). |
| Full engine: backtest + live | **LEAN** (QuantConnect) | Open-source institutional engine. The same code backtests *and* trades live through IBKR. Supports US equities, options, futures. This is the closest open-source thing to "what hedge funds use". |
| Engine alternative | **NautilusTrader** | Rust-core, very fast, actively developed, has an Interactive Brokers adapter. Steeper learning curve; keep it as a later option if you outgrow LEAN. |
| Direct IBKR access | **ib_async** | Clean Python wrapper for the IBKR API (the maintained successor of the well-known `ib_insync`). For custom scripts, your journal project, and quick experiments. |
| Data (prototype) | **yfinance** | Free Yahoo Finance downloader. Unofficial and occasionally flaky — perfect for learning, not for production. Upgrade paths in Phase 1. |
| Storage | **Parquet** files (+ **DuckDB** later) | Compact columnar files pandas reads instantly; DuckDB queries them with SQL when data grows. |
| Portfolio math (later) | **PyPortfolioOpt** / **Riskfolio-Lib** | Position sizing and portfolio optimisation libraries. |
| Options math (Phase 6) | **py_vollib**, **QuantLib** | Pricing and Greeks. |
| ML research (later) | **scikit-learn**, Microsoft **Qlib** | When you graduate from rules to learned models. |

Why LEAN as the backbone rather than wiring everything yourself: it gives you an event-driven backtester (defined in Part 3), corporate-action handling, an IBKR live connection, and a huge documentation base — the plumbing that takes months to write and debug alone. One honest caveat: LEAN suits daily-to-weekly strategies, which is exactly what you'll build; it is not the right tool for rapid intraday trading, and this roadmap deliberately doesn't go there — a solo daily-bar system is where the achievable edge and the manageable engineering meet.

---

## Part 3 — The four traps that kill new quant systems (and how this roadmap routes around each)

Naming these accurately up front is what makes the rest of the plan realistic rather than optimistic.

**Trap 1: Overfitting.** Tune a strategy's parameters until the backtest looks amazing, and you've built a description of the past, not a predictor of the future. *Route around it:* the Phase 2 ritual — decide rules before testing, keep a hard budget of ≤3 tunable parameters, develop on 2010–2019 data only, then run 2020-onwards exactly once as a verdict. Paper trading (Phase 4) is the final out-of-sample test.

**Trap 2: Bad data.** Two classics: unadjusted prices (splits and dividends create fake jumps) and **survivorship bias** — building your test universe from stocks that exist *today*, which quietly excludes every company that failed, flattering your results. *Route around it:* always use adjusted prices (the scripts below do); start knowingly with mega-caps where the bias is smallest; upgrade to a survivorship-bias-free data vendor (Phase 1 table) before you trust any strategy that picks from a wide universe.

**Trap 3: Ignoring costs.** A strategy that trades often can be profitable on paper and a donation to your broker in reality. *Route around it:* every backtest in this guide charges commissions plus **slippage** (the gap between the price you saw and the price you actually get) from day one, trades daily bars, and sticks to liquid names.

**Trap 4: Lookahead bias.** Accidentally using information you couldn't have had at decision time — e.g. trading at Monday's open using Monday's close. It's the most common silent bug in home-built backtests. *Route around it:* the code below uses an explicit "decide with yesterday's data, trade tomorrow" convention, and Phase 3's event-driven engine makes lookahead structurally hard, because it feeds your algorithm data one timestamp at a time, just like live trading.

**Expectations, stated plainly:** a realistic year-one outcome is a system that roughly matches or modestly beats buy-and-hold with meaningfully smaller drawdowns and zero emotional interference — which is precisely the consistency, predictability and robustness you named as the goal. Durable outperformance is a research grind measured in years; this pipeline is the vehicle you'll run that grind in. The first job of the system is to be *correct and safe*; being brilliant comes after.

---

## One EU-specific constraint to design around (worth knowing before writing any code)

As an EU retail client, IBKR will not let you buy **US-listed ETFs** (SPY, QQQ, EFA…) — the PRIIPs regulation requires a KID document US funds don't publish. Three practical routes around it, in the order you'll use them:

1. **Single US stocks are unaffected** — so this guide's prototype trades individual liquid US large caps, ensuring the backtest matches what your account can actually execute.
2. **UCITS equivalents** (e.g. CSPX on the LSE mirrors the S&P 500) exist when you later want ETF-style exposure.
3. **Options on US ETFs remain fully tradable** for you — relevant in Phase 6.

Index data (like the S&P 500 index itself) is still freely usable as a *signal* — you just can't buy the US-listed fund tracking it, and you won't need to.

---

## Phase 0 — Set up the workstation (one evening)

**Goal:** a Python environment where you can run quant code and notebooks.
**Done when:** a price chart renders from code you wrote.

**Step 1 — Install the three base tools.** Open PowerShell and run:

```powershell
winget install --id astral-sh.uv -e
winget install --id Git.Git -e
winget install --id Microsoft.VisualStudioCode -e   # skip if you already have VS Code
```

`uv` is a modern Python manager: it installs Python itself, creates isolated project environments, and installs packages — one tool instead of three.

**Step 2 — Create the project.** Close PowerShell, open a fresh one (so the new tools are on your PATH), then:

```powershell
mkdir C:\quant
cd C:\quant
uv init quantlab --python 3.12
cd quantlab
uv add pandas numpy matplotlib pyarrow jupyterlab ipykernel yfinance vectorbt quantstats
```

If `vectorbt` fails to install (it depends on a compiler library called numba that occasionally lags new Python versions), recreate with `--python 3.11` and repeat.

**Step 3 — Verify.**

```powershell
uv run python -c "import pandas, vectorbt, quantstats; print('environment OK')"
```

**Step 4 — Wire up VS Code.**
1. Open VS Code → `File` → `Open Folder…` → select `C:\quant\quantlab`.
2. Click the Extensions icon in the left bar (four squares) → search **Python** → Install (the one by Microsoft) → search **Jupyter** → Install.
3. `File` → `New File…` → name it `scratch.ipynb` → it opens as a notebook.
4. Top-right of the notebook, click **Select Kernel** → **Python Environments** → choose the one containing `.venv` (that's the environment uv just built).

**Step 5 — The test cell.** Paste this into the notebook cell and press Shift+Enter:

```python
import yfinance as yf
px = yf.download("AAPL", start="2020-01-01", auto_adjust=True)["Close"]
px.plot(title="AAPL — if you can see this chart, Phase 0 is done");
```

---

## Phase 1 — The data foundation (one weekend)

**Goal:** 15 years of clean daily prices for a universe of liquid US stocks, stored locally so every backtest is fast and reproducible.
**Done when:** the validation script prints a date range and no alarming gaps.

Two concepts first. **OHLCV** = the standard daily record per stock: Open, High, Low, Close prices plus Volume. **Adjusted close** = the close price retroactively corrected for splits and dividends, so historical returns are true; we always use it (`auto_adjust=True` below does this).

**Step 1 — Create `download_data.py`** in `C:\quant\quantlab`:

```python
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
```

```powershell
uv run python download_data.py
```

**Step 2 — Create `check_data.py`** and run it the same way. Never trust data you haven't checked:

```python
# check_data.py — sanity checks before trusting the data
import pandas as pd
px = pd.read_parquet("data/close.parquet")
print("Date range:", px.index.min().date(), "->", px.index.max().date())
print("Symbols:", px.shape[1])
print("\nMost missing data (fraction of days):")
print(px.isna().mean().sort_values(ascending=False).head(5).round(3))
print("\nMost 'stale' series (fraction of zero-move days — a red flag if high):")
print((px.pct_change() == 0).mean().sort_values(ascending=False).head(5).round(3))
```

A stock showing missing data before some date usually just IPO'd later (META, for example) — pandas handles that fine. Anything *else* odd: investigate before using.

**Step 3 — Know the honest limits of free data, and the upgrade path.** yfinance is unofficial and can break or rate-limit; the universe above also has mild survivorship bias (these are today's winners). Both are acceptable for the prototype and unacceptable for a system you trust with money. Upgrade options when you reach Phase 4–5 (verify current pricing — these move):

| Source | What you get | Rough cost |
|---|---|---|
| IBKR historical data (via API) | Good daily/intraday history for stocks you query; you already pay for the account | ~free, rate-limited |
| Norgate Data | Survivorship-bias-free US equities, delisted stocks included — the classic serious-hobbyist choice | ~US$30–40/mo |
| Nasdaq Data Link (Sharadar) | Equities + fundamentals, bias-free | ~US$50/mo |
| Polygon.io | Stocks + options, API-first | from ~US$29/mo |
| Databento | Institutional-grade, pay-as-you-go, incl. options (OPRA) | usage-based |

---

## Phase 2 — The prototype: your first honest backtest (2–3 weekends)

**Goal:** a rules-based strategy, backtested with costs, evaluated like a fund would, surviving an out-of-sample test. This is the prototype milestone.
**Done when:** you have `momentum_report.html` open in your browser and the strategy behaved acceptably on data it never saw during development.

### 2A — Hello world (30 minutes)

A vectorized backtest of the simplest possible rule — a moving-average crossover on one stock — just to see the machinery move. In a notebook:

```python
import vectorbt as vbt

price = vbt.YFData.download("AAPL", start="2015-01-01").get("Close")
fast, slow = vbt.MA.run(price, 20), vbt.MA.run(price, 100)
entries = fast.ma_crossed_above(slow)     # buy when 20-day avg crosses above 100-day
exits   = fast.ma_crossed_below(slow)     # sell on the reverse
pf = vbt.Portfolio.from_signals(price, entries, exits, fees=0.001, freq="1D")
print(pf.stats())
pf.plot().show()
```

Read the stats table. `Total Return` vs `Benchmark Return` tells you if the rule beat just holding; `Max Drawdown` (worst peak-to-trough loss) tells you what it would have cost you emotionally to hold on.

### 2B — The real prototype: cross-sectional momentum with a regime filter

The strategy — chosen because it's simple, academically well-documented, has only three parameters, and trades single US stocks (executable in your account):

1. Each month-end, rank the universe by **12-1 momentum** — the return over the past 12 months excluding the most recent month (the skip avoids a known short-term reversal effect).
2. Hold the top 5, equally weighted, for the next month.
3. **Regime filter:** if the S&P 500 *index* is below its 10-month moving average, hold cash instead. This is the piece that addresses what you said your discretionary approach lacks — a systematic answer to adverse short-term conditions.

Create `momentum_backtest.py`:

```python
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
```

```powershell
uv run python momentum_backtest.py
```

Line 2 of block 2 is the single most important line in this guide: `.shift(1)` means every position starts the day *after* the information existed. Internalise that pattern and you've dodged Trap 4 forever.

### 2C — The discipline ritual (this is what separates you from most hobbyists)

1. **Write the rules down before testing.** If you change a rule after seeing results, that's a new strategy — say so honestly in your notes.
2. **Parameter budget: three.** `TOP_N`, `LOOKBACK`, the regime window. Every extra knob multiplies the ways to fool yourself.
3. **Develop on 2010–2019 only.** Slice with `strat.loc["2011":"2019"]` while iterating.
4. **The one-shot verdict:** when you're satisfied, run 2020-onwards *once*. If performance collapses on data you never touched, the strategy was memorising the past — iterate on the idea, not the parameters, and repeat.
5. **Read the tearsheet like an allocator:** CAGR (compound annual growth rate) is the headline; Max Drawdown is what you'd actually live through; Sharpe ratio (return per unit of volatility — above ~0.8 is respectable for a simple long-only system) is the consistency score you're optimising for.

Variations worth testing *after* the base case, one at a time: top 3 vs top 10; a volatility-scaled version (size each position inversely to its recent volatility — a direct treatment of the short-term-volatility gap you want covered); weekly instead of monthly rebalancing (watch the costs line).

---

## Phase 3 — Move into the institutional engine: LEAN (2–4 weekends)

**Goal:** the same strategy running inside LEAN, QuantConnect's open-source engine — the step from "research script" to "trading system", because in LEAN the identical code later backtests, paper trades, and trades live.
**Done when:** a LEAN backtest of the momentum strategy produces results in the same ballpark as your Phase 2 script.

Why bother, when the script works? Your Phase 2 backtest is **vectorized** — it computes everything at once, which is fast but can hide subtle errors and can't place real orders. LEAN is **event-driven**: it feeds your algorithm one bar at a time and your code responds with orders, exactly like live trading. Same code, three environments.

**Step 1 — Install Docker Desktop** (LEAN runs its engine inside a container — a sealed, reproducible box, so "works on my machine" problems disappear):

```powershell
winget install --id Docker.DockerDesktop -e
```

Reboot if asked. If Docker complains about WSL2 (the Windows subsystem it runs on), open PowerShell **as Administrator**, run `wsl --install`, and reboot. Then launch Docker Desktop once and wait for the whale icon to report "Engine running". Docker Desktop is free for personal use.

**Step 2 — Create a free QuantConnect account** at quantconnect.com (needed for the CLI login and their data infrastructure). After signing up: your profile icon → **My Account** → note the **User ID** and **API Token**.

**Step 3 — Install the LEAN CLI and initialise a workspace:**

```powershell
uv tool install lean
lean --version
lean login          # paste User ID and API Token when prompted
mkdir C:\quant\lean-workspace
cd C:\quant\lean-workspace
lean init           # downloads the engine image and sample data
lean project-create "MomentumTop5" --language python
```

**Step 4 — Port the strategy.** Open `C:\quant\lean-workspace\MomentumTop5\main.py` in VS Code. LEAN's structure: an `initialize` method (set dates, cash, universe, and schedule a monthly rebalance) and event methods that receive data and place orders (`set_holdings("AAPL", 0.2)` targets a 20% position). Work through QuantConnect's free **Bootcamp** lessons (site → Learning) — the "Momentum" ones map almost one-to-one onto your Phase 2 rules. Expect this port to take a full weekend and to teach you more about your own strategy than Phase 2 did.

**Step 5 — Backtest, locally or in the cloud:**

```powershell
lean backtest "MomentumTop5"                  # local, uses data on disk
# or:
lean cloud push --project "MomentumTop5"
lean cloud backtest "MomentumTop5" --open     # runs on QC's servers with their full dataset, opens results
```

Honest data note: `lean init` ships only sample local data; full US equity history for *local* runs is bought with QC credits. The free workaround most people use: iterate logic locally on sample data, run full-history backtests in the cloud (free tier includes them, with quotas).

**Step 6 — Reconcile.** LEAN's results won't match your script exactly (it models fills and orders more realistically). Understand every material difference — this reconciliation habit is itself a hedge-fund practice, and it's how you find bugs before they cost money.

*Alternative engine, for later:* NautilusTrader — higher performance, actively developed, IBKR adapter included (currently requires Python 3.12/3.13). Revisit if you ever outgrow LEAN; don't start there.

---

## Phase 4 — Paper trading on IBKR (one weekend to set up, then 4–8 weeks running)

**Goal:** the system trades a simulated IBKR account, unattended, through real market conditions.
**Done when:** it has run for several weeks, its fills match backtest expectations, and nothing required emergency intervention.

**Step 1 — Create your paper account.** IBKR Client Portal → profile icon (top right) → **Settings** → **Account Settings** → under *Configuration*, find **Paper Trading Account** → follow the prompts. You'll receive a separate paper username; set its password. It can take up to a day to activate. While there, enable **"Share real-time market data with paper trading account"** so the paper account sees the live quotes your subscriptions already pay for.

**Step 2 — Install IB Gateway** (TWS without the screens — lighter, made for APIs). IBKR website → Technology → **IB Gateway** → download **Stable** for Windows → install → log in with the **paper** credentials (select the Paper mode toggle on the login screen). Convenient side-effect: paper credentials don't trigger the mobile-app two-factor prompt, so unattended running is simpler than with a live login.

**Step 3 — Open the API door.** In IB Gateway: **Configure** → **Settings** → **API** → **Settings**:
1. Tick **Enable ActiveX and Socket Clients**.
2. Untick **Read-Only API** (the system must place orders).
3. Confirm **Socket port** = `4002` (Gateway's paper port; TWS paper uses `7497`).
4. Add `127.0.0.1` to **Trusted IPs**.
5. Under **Lock and Exit**, set **Auto restart** — IBKR forces a nightly restart; this setting makes Gateway survive it without you.

**Step 4 — Route A (recommended): let LEAN drive.**

```powershell
cd C:\quant\lean-workspace
lean live "MomentumTop5"
```

The wizard asks for a brokerage (**Interactive Brokers**), your paper username/password/account number, and a data feed (choose Interactive Brokers to use your own subscriptions). LEAN then runs your algorithm continuously against the Gateway.

**Step 5 — Route B (for your custom scripts and the journal):** talk to the same Gateway directly with `ib_async`:

```powershell
uv add ib_async
```

```python
from ib_async import IB, Stock, MarketOrder

ib = IB()
ib.connect("127.0.0.1", 4002, clientId=7)      # 4002 = IB Gateway, paper
c = Stock("AAPL", "SMART", "USD")
ib.qualifyContracts(c)
trade = ib.placeOrder(c, MarketOrder("BUY", 1))
ib.sleep(3)
print("Order status:", trade.orderStatus.status)
ib.disconnect()
```

Seeing that one simulated share fill is a genuine milestone: your code just traded.

**Step 6 — Run it for 4–8 weeks minimum.** This period exists to surface everything backtests can't: restarts, data hiccups, partial fills, your own itch to interfere. Log every event. Compare weekly against the backtest's expectations, and log system-vs-discretionary performance in your journal — that comparison data is exactly the feedback loop you wanted for refining your manual strategies.

---

## Phase 5 — Go live, small, with a risk module (ongoing)

**Goal:** real money, hard limits, full observability.
**Done when:** three live months where every deviation from paper behaviour has an explanation.

**Step 1 — Hard-code the risk rules.** These live in code, not in your head, and the system refuses to trade when one is breached. Sensible v1 defaults:

| Rule | v1 default |
|---|---|
| Max weight per position | 10% of system capital |
| Max gross exposure | 100% — the system itself uses no leverage in v1 |
| Daily kill-switch | halt all trading if the system book drops 3% in a day; require manual re-arm |
| Order sanity | reject any order priced >2% from last trade, or larger than 25% of the target position |
| Activity cap | max 2× the expected number of orders per day — a runaway-loop breaker |
| Heartbeat | if the strategy process hasn't checked in for 15 minutes during market hours, alert |

**Step 2 — Monitoring.** Python's `logging` module to a dated file for every decision, order, fill and error; alerts (email via `smtplib`, or a Telegram bot — both ~20 lines) for fills, rule breaches, and heartbeat failures. Extend your trade journal to tag every order **SYSTEM** or **MANUAL** so attribution stays clean — that tag also keeps the audit trail tidy for tax records.

**Step 3 — Size the allocation like an engineer.** Start with a slice of trading capital sized so that its total loss would be annoying, not damaging — 5–10% is a common starting range — and scale it up as live results track paper results. The scaling rule is the point: allocation follows demonstrated reliability, not enthusiasm.

**Step 4 — Ops.** Simplest reliable setup: your PC stays on during US market hours with Gateway auto-restart configured, and Windows **Task Scheduler** launches the strategy script on a schedule (Start → type "Task Scheduler" → Create Basic Task → point it at `uv run python your_script.py` in the project folder). When that gets old, a small VPS (~€5–10/mo) runs the same stack around the clock; dockerised IB Gateway images exist for exactly this.

---

## Phase 6 — Extend to options and other derivatives (after Phase 5 is stable)

The honest problem first: historical **options** data is the expensive, bulky input in retail quant — full chains (every strike and expiry, every day) run to terabytes, and IBKR's API only serves limited history. That's a solvable sequencing problem, not a wall:

1. **Start with structures that don't need chain history to prototype.** Systematic covered calls, cash-secured puts, and defined-risk verticals on liquid US large caps can be first-approximated from underlying prices plus a volatility estimate — enough to test the *rules* (when to sell, which delta, when to roll) before buying data.
2. **Use LEAN's native options support next.** The engine handles US options chains, Greeks and assignment, and cloud backtests can use QuantConnect's options data within free-tier quotas — the cheapest way to validate a chain-aware version.
3. **Buy data only for what survives steps 1–2.** Polygon.io's options tier (from ~US$29/mo), Databento's OPRA feed (pay-as-you-go), or ORATS (research-grade options analytics) — sized to the one or two strategies that earned it.
4. **Tooling:** `py_vollib` for Black-Scholes prices and Greeks; QuantLib when you eventually want more exotic modelling. Execution through the same IBKR pipeline you built — and note options on US ETFs are open to you even where the ETFs themselves aren't.
5. **Futures are the quieter alternative** for "derivatives": continuous-contract data is far cheaper than options chains, LEAN supports them natively, and trend-following on futures is the single most-documented systematic strategy family in existence.

---

## The weekly operating rhythm (once live)

Saturday morning, ninety minutes: read the week's logs; reconcile live fills against expectations; note one research idea in the backlog (don't chase it mid-week); monthly, write a one-paragraph letter to yourself comparing the system book vs your discretionary book — that document, over a year, becomes your single most valuable dataset.

Deployment rule: changes to live code happen on weekends, after a fresh backtest, never during market hours.

---

## Glossary

- **Backtest** — replaying trading rules on historical data to estimate how they'd have performed.
- **OHLCV** — Open, High, Low, Close, Volume: the standard daily bar.
- **Adjusted close** — close price corrected for splits/dividends so returns are true.
- **Universe** — the set of instruments a strategy is allowed to pick from.
- **Signal** — a rule's output: what to hold, when.
- **Factor** — a measurable characteristic (momentum, value, volatility) with predictive evidence.
- **Vectorized backtest** — computes the whole history at once; fast, great for research.
- **Event-driven backtest** — feeds data bar-by-bar and takes orders, mimicking live trading.
- **Lookahead bias** — using information before it existed; the classic silent backtest bug.
- **Survivorship bias** — testing only on stocks that still exist today, flattering results.
- **Overfitting** — tuning until a strategy memorises the past instead of capturing a real effect.
- **Out-of-sample** — data deliberately untouched during development, used as the final exam.
- **Walk-forward** — repeatedly re-fitting on a rolling window and testing on the next slice.
- **Slippage** — the gap between the expected and actual execution price.
- **Turnover** — how much of the portfolio changes per period; the multiplier on your costs.
- **Drawdown** — decline from a peak; *max* drawdown is the worst one.
- **Sharpe ratio** — average return divided by volatility; the standard consistency score.
- **CAGR** — compound annual growth rate.
- **Regime filter** — a market-level condition (e.g. index above its moving average) gating risk-on/off.
- **Rebalance** — the periodic act of moving actual positions to target positions.
- **Paper trading** — live trading against a simulated account.
- **Tearsheet** — a one-page fund-style performance report.
- **Kill-switch** — a hard-coded condition that halts all trading until manually re-armed.

---

## Learning resources, in the order to consume them

1. **Ernest Chan — *Quantitative Trading*** — the best first book; written for exactly your situation (technical person, retail account, building alone).
2. **QuantConnect Bootcamp + docs** — free, interactive, and directly reusable in Phases 3–4.
3. **Meb Faber — "A Quantitative Approach to Tactical Asset Allocation"** — free on SSRN; the 10-month moving-average regime filter comes from here.
4. **Gary Antonacci — *Dual Momentum Investing*** — the momentum evidence base behind Phase 2.
5. **Robert Carver — *Systematic Trading*** — the best book ever written on position sizing and risk for solo systematic traders; read before Phase 5. His `pysystemtrade` repo on GitHub is a complete reference implementation.
6. **Stefan Jansen — *Machine Learning for Algorithmic Trading*** — plus its large free GitHub repo; your bridge from rules to models.
7. **Quantopian Lectures** — the archived notebook series on GitHub; still the best free statistics-for-trading course.
8. **Marcos López de Prado — *Advances in Financial Machine Learning*** — advanced; only after the pipeline is live and boring.
9. **r/algotrading wiki** — good reality checks and tooling threads.

---

## Appendix — Phase 0–1 commands in one block

```powershell
winget install --id astral-sh.uv -e
winget install --id Git.Git -e
winget install --id Microsoft.VisualStudioCode -e
# --- new PowerShell window ---
mkdir C:\quant; cd C:\quant
uv init quantlab --python 3.12
cd quantlab
uv add pandas numpy matplotlib pyarrow jupyterlab ipykernel yfinance vectorbt quantstats
uv run python -c "import pandas, vectorbt, quantstats; print('environment OK')"
# create download_data.py and check_data.py from Phase 1, then:
uv run python download_data.py
uv run python check_data.py
```

*Nothing here is financial advice — it's an engineering plan for a system whose trading decisions remain yours.*
