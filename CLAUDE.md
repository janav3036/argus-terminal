# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

This repo is a **skeleton only** — folders, `__init__.py` stubs, and empty entry-point
files (`main.py`, `app.py`, `module_registry.py`). No implementation exists yet: no
base classes, no requirements file, no test runner, no lint config. Do not assume any
of these exist without checking first.

The full design is specified in `argus_brief.md` at the repo root — read it before
doing any nontrivial work here. It is the single source of truth for the intended
architecture, module list, data flow, and aesthetic. This file only adds things not
already obvious from the brief once code exists.

## What Argus is

A PySide6 desktop "terminal" that consolidates four existing standalone quant
research projects plus six new modules into one persistent app. It is not being
built from scratch — it's an integration layer over existing code.

## Source projects (imported, not reimplemented)

The four "Project N" backends referenced in `argus_brief.md` live as **sibling
directories** under `~/Programs/`, outside this repo:

| Brief name | Path | Provides |
|---|---|---|
| Project 1 — Heston Calibration Engine | `~/Programs/heston_sde/` | `calibration/`, `models/` (black_scholes, characteristic_fn, heston_fft, heston_lewis) |
| Project 2 — LOB Microstructure Lab | `~/Programs/Limit Order Book/` | `recorder/bybit_ws.py` (live Bybit WS feed), `models/predictor.py`, `config/settings.py` |
| Project 3 — Monte Carlo Pricing Engine | `~/Programs/MonteCarlo/` | `models/` (gbm, heston_mc, merton_mc, bates_mc), `payoffs/`, `variance_reduction/` |
| Project 4 — Stochastic Interest Rate Models | `~/Programs/InterestRate/` | `models/` (vasicek, cir, hull_white), `data/rbi_loader.py`, `pricing/` (bond_pricing, caps_floors, yield_curve) |

All four are proper Python packages. `Limit Order Book` has a space in its folder
name — handle that in any `sys.path` / import wiring. Argus modules should import
these as libraries rather than duplicating their logic.

Data source status: the Bybit WS feed (Project 2) is confirmed working. NSE options
chain and the RBI/CCIL yield pipeline are unconfirmed — verify before building
`data/nse_feed.py` or `data/rbi_feed.py` against them.

## Architecture (per the brief — implement to this shape)

- **Module pattern**: every module is a `ArgusModule` subclass in `modules/<name>/`
  implementing `get_sidebar_label()`, `get_status_preview()`, and `build_widget()`.
  Modules are registered in a single list in `module_registry.py` — the sidebar,
  home page nav cards, and status bar all auto-discover from that one registry.
  Adding a module should never require touching home-page or sidebar code directly.
- **Data threads**: live data sources subclass `ArgusDataThread` (`core/base_thread.py`)
  and run as persistent background threads/QThreads, pushing updates to widgets via
  Qt signals. The UI thread must never block on I/O.
- **Two-layer charting**: `pyqtgraph` for anything live/tick-updating (LOB heatmap,
  intraday price charts). `Plotly` rendered to HTML and shown via `QWebEngineView`
  for complex analytical charts (3D IV surfaces, yield curve comparisons, PCA
  loadings) — this is how existing Plotly code from the source projects gets reused
  unmodified.
- **Persistence**: SQLite (`core/cache.py`) caches fetched data locally so the app
  can launch with recent data even when external feeds are down; each module
  restores its last-known state on launch.
- Cross-module data sharing exists (e.g. Options Pricer module pulls calibrated
  Heston/Bates params from the Volatility Lab module; Vol Regime output feeds both
  the home page conditions panel and the Risk Engine module) — when building a
  module, check whether the brief specifies it consumes another module's output.

## Module→source mapping

Modules 1–4 wrap the four source projects above (Volatility Lab↔Project 1, Order
Book↔Project 2, Options Pricer↔Project 3, Rates↔Project 4). Modules 5–10
(Vol Regime, Yield PCA, Risk Engine, Factor Analyzer, Stat Arb, Strategy Builder)
are new — no existing backend to wrap, build the quant logic as part of the module.

## Commands run so far

No build/lint/test tooling exists yet (see "Current state" above). The commands
below are the actual shell history for how this repo reached its present state —
kept here so future sessions know what's already been done and don't redo it.

Skeleton scaffold (2026-07-09) — folders + empty stub files, no implementation:

```bash
# from the repo root
mkdir -p core data home tests assets/icons assets/styles \
  modules/volatility_lab modules/order_book modules/options_pricer modules/rates \
  modules/vol_regime modules/yield_pca modules/risk_engine modules/factor_analyzer \
  modules/stat_arb modules/strategy_builder

touch main.py app.py module_registry.py assets/styles/argus_dark.qss

for d in core data home modules tests \
  modules/volatility_lab modules/order_book modules/options_pricer modules/rates \
  modules/vol_regime modules/yield_pca modules/risk_engine modules/factor_analyzer \
  modules/stat_arb modules/strategy_builder; do
  touch "$d/__init__.py"
done
```

Note: the repo root itself does **not** get an `__init__.py` — it's the directory
you run `main.py` from, not a package (matches the brief's repo-structure tree,
which shows no `__init__.py` at that level).

As new setup/build/run commands get established (venv creation, `pip install`,
`python main.py`, test invocation, linting), add them here as their own dated
subsection rather than editing this one, so the history stays intact.

Venv + PySide6 install (2026-07-10):

```bash
# system python3 resolved to 3.14.5 (too new — no PySide6 wheels yet);
# used Homebrew's python3.12 instead
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install PySide6
pip freeze | grep -i pyside6 > requirements.txt   # pinned: PySide6==6.11.1
```

To resume work in later sessions: `source .venv/bin/activate` from the repo root.
