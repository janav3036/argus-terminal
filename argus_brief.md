# Argus — Quantitative Market Intelligence Terminal

*A quantitative market intelligence terminal for Indian markets.*

Named after Argus Panoptes, the hundred-eyed giant of Greek mythology who watches
everything simultaneously. The app monitors equities, volatility, microstructure,
rates, risk, and macro conditions in a single persistent desktop application — each
"eye" is a module, all watching at once.

---

## Vision

Argus is a PySide6 desktop application that consolidates quantitative research tools,
live market data, and analytical models into a single institutional-grade terminal.
It is not a dashboard in the conventional sense. It is a modular, extensible platform
where each module is a self-contained quantitative application — backed by real models,
real data, and real infrastructure built across a series of research projects.

The target experience: open Argus in the morning, get a complete picture of Indian
market conditions in under 30 seconds, then drill into any domain with one click.

The design principle: every number on screen is computed, not decorative. Every chart
represents a model output or a live data feed. Nothing is hardcoded or illustrative.

---

## Technical Stack

**Application framework:** PySide6 (Qt for Python — official binding, LGPL licensed).
Qt is the industry standard for financial desktop software. Bloomberg Terminal is
built on Qt. The choice signals professional intent.

**Charting — two-layer strategy:**
- **pyqtgraph** for all real-time, live-updating components. Native Qt, renders at
  the speed required for tick-by-tick LOB data and live price feeds.
- **Plotly via QWebEngineView** for complex analytical charts — 3D IV surfaces, yield
  curve comparisons, convergence plots, factor attribution charts. QWebEngineView
  is a full Chromium renderer embedded inside a Qt widget. All existing Plotly code
  from the research projects works unmodified; figures are serialized to HTML and
  served into the widget.

**Backend threading model:**
All data feeds run as persistent background threads (QThread or Python threading),
pushing updates to the UI via Qt signals. The UI thread never blocks on I/O. Data
sources include:
- `yfinance` — Indian indices, FX, commodities (NIFTY, SENSEX, NIFTY Bank, INR/USD,
  Gold, Crude)
- **Bybit WebSocket** — live L2 order book feed, already running from Project 2
- **RBI / CCIL data pipeline** — yield curve data, from Project 4
- **NSE options data** — NIFTY options chain, from Projects 1 and 3
- **RSS feeds** — Economic Times Markets, Mint, MoneyControl, for the news module
- Existing project backends (calibration engines, LOB reconstruction, MC pricer,
  rate models) are imported as Python modules — Argus does not reimplement them

**Persistence:** SQLite for caching fetched data locally (indices, news, yield curves)
to allow the app to load with recent data even when external feeds are unavailable.
Each module's last-known state is stored and restored on app launch.

---

## Application Layout

### Persistent Elements (always visible, every page)

**Top bar — live market strip**
Updates every 5 seconds via yfinance polling. Displays:
```
NIFTY 50  |  NIFTY Bank  |  India VIX  |  SENSEX  |  INR/USD  |  Gold  |  Crude
22,450 ▲0.34%  |  48,120 ▲0.21%  |  13.4 ▼2.1%  ...
```
Each instrument shows price + absolute change + percentage change. Green on positive
moves, red on negative. The top bar persists across every page of the application.

**Left sidebar — module navigation**
Fixed-width vertical list of all available modules. Current module highlighted.
Each entry shows the module name and a one-line live status indicator
(e.g. "Volatility Lab — Last calibrated 9:45 AM").

**Status bar — data connection states (bottom of screen)**
Shows live/stale/disconnected status for each data source:
```
Bybit WSS: ● Live  |  NSE Options: ● Live  |  RBI Curve: ⚠ 2h ago  |  yfinance: ● Live
```
Any disconnection is immediately visible at the bottom of every screen.

---

## Home Page

The landing page. Purpose: give a complete picture of current market conditions
in under 30 seconds.

### Layout — three columns

**Left column: News Feed**
Live-updating RSS aggregator pulling from Economic Times Markets, Mint, and MoneyControl.
Refreshes every 5 minutes. Each item shows:
- Headline (truncated to two lines)
- Source and timestamp
- Clickable — opens full article in system browser

Scrollable list, newest at top. No summarization or AI processing — raw headlines only.
The purpose is to give market context alongside the quantitative views in other modules.

**Center column: Market Overview**
Two components stacked vertically:

*Fixed watchlist OHLC chart (top half):*
pyqtgraph candlestick chart (reusing the `CandlestickItem` built for Module 2) over a
small fixed watchlist of instruments, not free-text search — a tab/selector per symbol,
same interaction pattern as the Order Book module. Data comes from `yfinance`, which
serves **delayed** NSE/BSE quotes (~15-20 min lag) — polled on a refresh timer like the
existing top bar feed, not a true tick stream. This replaces the originally-specified
single-NIFTY-50 rolling line chart. Watchlist membership and refresh interval TBD.

**v2 idea, not scoped:** free-text stock search instead of/alongside the fixed list —
deferred since it requires spinning up a data thread on demand per searched symbol
rather than the fixed set of long-lived threads used everywhere else in the app.

*NIFTY 50 Sector Heatmap (bottom half):*
Treemap-style grid — each sector as a colored tile, sized by market cap weight,
colored by daily return (green → red scale). Sectors: IT, Banking, Financial Services,
FMCG, Auto, Pharma, Energy, Metal, Realty, Media. Built with pyqtgraph or a Plotly
embed — whichever renders more cleanly.

**Right column: Market Conditions**
Three sub-panels stacked vertically:

*Volatility conditions:*
- India VIX value + 30-day realized vol → variance risk premium (VIX - RV)
- Regime label from the HMM Volatility Regime module: LOW / ELEVATED / CRISIS
- Confidence score (%) for the current regime classification

*Yield curve snapshot:*
Small Plotly line chart showing the current Indian G-Sec term structure (3M → 30Y),
pulled from Project 4's RBI data pipeline. Curve shape label: NORMAL / FLAT / INVERTED.
10Y yield prominently displayed.

*FX and commodities:*
INR/USD, Gold (MCX), Crude (MCX) — current price, daily change, 5-day sparkline each.

### Bottom: Module Navigation Cards
Horizontal row of clickable cards — one per module. Each card shows:
- Module name + icon
- A live one-line preview of that module's current state
- Click navigates to the full module page

Cards (left to right):
```
Volatility Lab          Order Book              Options Pricer
ATM IV: 14.3%           Spread: 1.2 bps         Last: Asian Call
Skew: -0.8%/Δ          OFI: -0.34 (bearish)    Model: Bates
Cal: 9:45 AM            ● Live                   N=100k paths

Rates                   Risk Engine             Signals
10Y: 6.87%              VaR (1d): -1.24%        Active pairs: 3
Curve: Normal           CVaR: -1.81%            Top z-score: 2.41
HW fitted: 9:30 AM      Regime: Low Vol         HDFC/ICICI: LONG
```

---

## Modules

### Module 1 — Volatility Lab
*Source: Project 1 (Heston Calibration Engine)*

Live NIFTY options chain displayed as a table (all strikes × expiries, with market
IV and Heston-fitted IV side by side). 3D implied volatility surface rendered via
Plotly embed — market surface and Heston-fitted surface as two overlapping meshes.
IV smile chart for selected expiry: market vs BS vs Heston vs Bates. Calibrated
Heston parameters (κ, θ, σ, ρ, v₀) displayed with a recalibrate button. BS vs
Heston pricing error heatmap by moneyness bucket.

---

### Module 2 — Order Book
*Source: Project 2 (LOB Microstructure Lab)*

Price-time heatmap: x-axis time, y-axis price levels, color intensity = order volume
at each level. This is what a trading desk LOB screen looks like. Rendered via
pyqtgraph for live performance. Below the heatmap: live microstructure metrics
(OFI, realized spread, effective spread, Kyle's lambda, queue position) all updating
tick by tick. Direction predictor confidence score displayed as a gauge (bullish /
neutral / bearish). Instrument selector: BTCUSDT, ETHUSDT, or the third recorded
instrument from Project 2.

**v1 scope (2026-07-13):** `features/microstructure.py` in Project 2 only provides
mid price, spread, relative spread, order-book imbalance, and microprice — ship v1
with those, driven off a live `OrderBook` fed by `recorder/bybit_ws.py` rows.
Deferred to v2, not yet buildable against the source project as it stands:
- **Realized/effective spread, Kyle's lambda, queue position** — no implementation
  exists in Project 2; need to be derived/added there first.
- **Direction predictor gauge** — `models/predictor.py`'s `DirectionPredictor`
  trains on demand from parquet datasets and has no persisted/pretrained model;
  needs a training + persistence story before it can back a live gauge.

---

### Module 3 — Options Pricer
*Source: Project 3 (Monte Carlo Pricing Engine)*

Interactive Monte Carlo pricer. User selects: underlying (NIFTY spot), option type
(European / Asian / Barrier / Lookback), model (GBM / Heston / Merton / Bates),
variance reduction method (None / Antithetic / Control Variate / Stratified / QMC),
and number of paths. On run, displays: price ± 95% confidence interval, standard
error, runtime. Live convergence chart (price estimate vs N paths, with CI bands
narrowing as paths increase). Exotic payoff diagram (visual representation of the
payoff structure). For calibrated runs, pulls Heston/Bates parameters from the
Volatility Lab module automatically.

---

### Module 4 — Rates
*Source: Project 4 (Stochastic Interest Rate Models)*

Three-model yield curve display: Vasicek, CIR, and Hull-White fitted curves overlaid
on the market G-Sec curve. Model selector to toggle each on/off. Calibrated parameters
table (κ, θ, σ, AIC for each model). Yield curve PCA decomposition (see Module 6 below —
results fed here as well). Rate path fan chart: 5-year simulated rate distribution,
5th/25th/50th/75th/95th percentile bands. Cap/floor pricer: select notional, strike,
tenor, and flat vol — outputs cap price, floor price, and parity check.

---

### Module 5 — Volatility Regime Detector
*New short project — 1–2 weeks*

Hidden Markov Model trained on NIFTY realized volatility (30-day rolling window).
Two-state model (Low Vol / High Vol) or three-state (Low / Elevated / Crisis).
Outputs: regime timeline overlaid on NIFTY price history (color-coded bands),
current regime + posterior probability, transition matrix visualization, realized
vol distribution per regime (histogram). This output also feeds the home page
conditions panel and the Risk Engine module. HMM implemented via `hmmlearn`.

---

### Module 6 — Yield Curve PCA
*New short project — 1 week*

PCA on daily G-Sec yield changes (using the historical RBI data from Project 4,
so no new data pipeline needed). Three principal components extracted and labeled
as Level (parallel shift), Slope (short vs long end), and Curvature (belly move).
Displays: explained variance by component (scree plot), factor loadings across
tenors for each component, historical factor scores (time series of how each factor
has evolved), and current yield curve decomposed into L/S/C contributions. This
is one of the most elegant empirical results in fixed income and will be immediately
recognizable to anyone on a rates desk.

---

### Module 7 — Portfolio Risk Engine
*New short project — 2 weeks*

Portfolio construction UI: add any NIFTY 50 constituents by ticker, set weights.
Computes and displays:
- **Historical VaR** (1-day, 5-day at 95% and 99% confidence) via empirical return
  distribution
- **Parametric VaR** (variance-covariance method, assumes normality)
- **Monte Carlo VaR** (GBM simulation, N=10,000 paths, 1-day horizon)
- **CVaR / Expected Shortfall** for all three methods (the tail beyond VaR)
- Return distribution histogram with VaR and CVaR marked
- Rolling VaR chart (VaR estimate over the last 252 trading days)
- Correlation matrix heatmap for current portfolio

CVaR is now the Basel III regulatory standard — more defensible than VaR alone.
Data via yfinance historical prices.

---

### Module 8 — Factor Exposure Analyzer
*New short project — 2 weeks*

Given any NIFTY stock or portfolio, decompose returns into Fama-French factors.
Factors computed from Indian market data (NSE universe):
- **Market (Mkt-RF):** NIFTY 50 excess return
- **Size (SMB):** Small-cap vs large-cap return spread
- **Value (HML):** High book-to-market vs low book-to-market spread
- **Momentum (MOM):** 12-1 month return spread

Outputs: OLS regression of portfolio returns on factors (coefficients + t-stats +
R²), factor exposure bar chart, rolling 60-day beta to each factor, residual
(alpha) time series. The factor construction from raw NSE data is the meaningful
quantitative work here — standard Fama-French datasets do not exist for India, so
building the factor series from scratch is genuinely novel.

---

### Module 9 — Statistical Arbitrage Monitor
*New short project — 2 weeks*

Screen NIFTY 50 pairs for cointegration using Engle-Granger test. For each
cointegrated pair above a significance threshold, estimate the dynamic hedge ratio
via a Kalman filter (hedge ratio evolves over time rather than being fixed — this
is the meaningful upgrade over naive pairs trading). Displays:
- Pair screener table: all pairs ranked by cointegration p-value
- Live z-score chart for selected pair (spread vs ±1, ±2 sigma bands)
- Kalman filter hedge ratio evolution over time
- Paper P&L for a simple mean-reversion strategy (long when z < -2, short when z > 2)
- Active signals: pairs currently at entry threshold

Data via yfinance. New mathematics: Kalman filter, Engle-Granger cointegration test
(via `statsmodels`).

---

### Module 10 — Options Strategy Builder
*New short project — 1 week*

Multi-leg options strategy constructor using the pricing engine from Project 1.
User adds legs (call/put, strike, expiry, long/short, quantity). Displays:
- Payoff diagram at expiry (P&L vs underlying price)
- Current P&L given today's spot
- Aggregated Greeks: total delta, gamma, vega, theta across all legs
- Greeks profile chart: how each Greek evolves across the strike range
- Break-even points labeled on the payoff diagram

Common strategy templates pre-loaded as buttons: Long Call, Long Put, Covered Call,
Straddle, Strangle, Bull Call Spread, Bear Put Spread, Iron Condor, Butterfly.
Each template pre-populates the leg builder; user can then modify. All pricing
runs through the Heston calibration engine (if calibration is fresh) or falls back
to Black-Scholes. This module makes Project 1 interactive and usable.

---

## Mutability Model

Argus is explicitly designed to grow. Adding a new module requires only three things:

1. **A new Python file** in `argus/modules/` that subclasses the `ArgusModule` base
   class and implements three methods: `get_sidebar_label()`, `get_status_preview()`
   (the one-line text shown on the home page navigation card), and `build_widget()`
   (returns the full QWidget for the module page).

2. **Registration** in `argus/module_registry.py` — a single list of module classes.
   The sidebar, navigation cards, and status bar automatically discover and display
   registered modules. No other files need to change.

3. **A background data thread** (optional) if the module needs live data — subclasses
   `ArgusDataThread` and emits Qt signals that the module widget connects to.

The home page navigation cards are auto-generated from the registry. Adding a module
to the registry makes it appear everywhere (sidebar, home page card, status bar)
without touching the home page code.

This means Argus does not have a fixed feature set. Every future research project —
whether it is a credit model, an RL execution agent, a regime-switching portfolio
optimizer, or anything else — can be added as a module in a day, immediately
inheriting the full app infrastructure (live top bar, navigation, data connections,
status monitoring, local caching).

The app is the platform. The modules are the projects.

---

## Repository Structure

```
argus/
├── main.py                        # application entry point
├── app.py                         # QApplication setup, main window
├── module_registry.py             # list of all registered ArgusModule subclasses
├── core/
│   ├── base_module.py             # ArgusModule abstract base class
│   ├── base_thread.py             # ArgusDataThread base class
│   ├── top_bar.py                 # persistent live market strip
│   ├── sidebar.py                 # navigation sidebar
│   ├── status_bar.py              # data connection status bar
│   └── cache.py                   # SQLite local data cache
├── data/
│   ├── yfinance_feed.py           # indices, FX, commodities thread
│   ├── bybit_feed.py              # LOB WebSocket thread (from Project 2)
│   ├── nse_feed.py                # options chain data thread
│   ├── rbi_feed.py                # yield curve data thread (from Project 4)
│   └── rss_feed.py                # news RSS scraper thread
├── home/
│   ├── home_page.py               # home page layout
│   ├── news_panel.py              # left column: news feed
│   ├── market_panel.py            # center column: NIFTY chart + sector heatmap
│   ├── conditions_panel.py        # right column: vol regime, yield curve, FX
│   └── nav_cards.py               # bottom module navigation cards
├── modules/
│   ├── volatility_lab/            # Module 1 — Heston/IV surface
│   ├── order_book/                # Module 2 — LOB live screen
│   ├── options_pricer/            # Module 3 — MC exotic pricer
│   ├── rates/                     # Module 4 — IR models + yield curve
│   ├── vol_regime/                # Module 5 — HMM regime detector
│   ├── yield_pca/                 # Module 6 — yield curve PCA
│   ├── risk_engine/               # Module 7 — VaR / CVaR
│   ├── factor_analyzer/           # Module 8 — Fama-French
│   ├── stat_arb/                  # Module 9 — pairs trading monitor
│   └── strategy_builder/          # Module 10 — options strategy builder
├── assets/
│   ├── icons/                     # module icons, app icon
│   └── styles/
│       └── argus_dark.qss         # Qt stylesheet (dark terminal theme)
└── tests/
```

---

## Aesthetic

Dark terminal theme throughout. Qt stylesheet (`.qss`) applied globally. Color palette:
- Background: near-black (`#0D0D0D`)
- Panel backgrounds: dark grey (`#141414`, `#1A1A1A`)
- Borders: subtle (`#2A2A2A`)
- Accent: steel blue (`#2B5EA7`) — matching the LaTeX report accent from Project 2
- Positive: muted green (`#2ECC71`)
- Negative: muted red (`#E74C3C`)
- Text: off-white (`#E8E8E8`)
- Secondary text: grey (`#888888`)

Typography: monospaced for all numbers (price, yield, vol figures) — either JetBrains
Mono or Fira Mono. Proportional sans-serif for labels and descriptions.

The aesthetic goal is not to look like a Python GUI. It should look like internal
tooling at a quant fund.

---

## Deliverables

1. Public GitHub repo (`argus`) with comprehensive README including screenshots
2. Fully working application: all 10 modules functional, home page live
3. One demo video (2–3 minutes) showing the app navigating through modules with
   live data — this is the portfolio artifact, not just the code
4. `MODULES.md` — developer documentation explaining how to add a new module,
   as a demonstration that the architecture is genuinely extensible

---

## Strategic Positioning

Argus is not a project. It is evidence of systems thinking.

Each of the four core research projects (Heston, LOB, Monte Carlo, Interest Rates)
produced a rigorous but standalone artifact. Argus demonstrates the ability to
synthesize them into a coherent, deployable system with real infrastructure — data
threading, live feeds, module isolation, persistent caching — of the kind that
actually exists at quant firms.

The new modules (Regime Detector, Yield PCA, Risk Engine, Factor Analyzer, Stat Arb,
Strategy Builder) introduce six new quantitative domains in minimal time, because the
platform infrastructure is already there. Each one would otherwise require a standalone
project; inside Argus they ship as modules.

For MFE applications: the combination of four deep research projects plus a deployed
terminal application is an unusual portfolio. Most applicants have papers or notebooks.
A working terminal demonstrates that the quantitative work is not academic in the
pejorative sense — it was built to be used.

For buy-side internship conversations: Argus is a 60-second demo. Open it, navigate
through two or three modules, show the live data, show a calibrated Heston surface.
That is more memorable than any resume bullet.
