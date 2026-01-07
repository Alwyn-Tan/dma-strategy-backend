# Change: Add advanced DMA strategy structure (regime + ensemble + vol targeting)

## Why
The current dual moving average (DMA) MVP is structurally vulnerable to choppy markets and slow exits, leading to high drawdowns and unstable performance.
Industry-standard trend/CTA practice improves robustness by changing strategy structure (filters, position sizing, and risk controls) rather than only tuning MA parameters.

## What Changes
- Add an **optional** `strategy_mode=advanced` for backtest/performance calculation that layers:
  - Regime filtering (e.g., only long when `close > MA200`, optional `ADX` trend-strength gate)
  - Signal ensembling across multiple MA pairs to reduce parameter-selection bias
  - Volatility targeting (inverse-vol scaling) to stabilize risk and reduce drawdowns in high-vol regimes
  - ATR-based risk controls (optional trailing stop / volatility stop) in the performance engine
- Keep default behavior **unchanged** (`strategy_mode=basic`) to avoid breaking existing clients.
- Extend API query parameters and response `meta.assumptions` to capture advanced-mode configuration.

## Impact
- Affected specs:
  - `stocks-api` (query params, response contract)
  - `strategy-engine` (signal/position sizing/backtest semantics)
- Affected code (expected):
  - `api/serializers.py` and `api/views.py` (serializers + endpoint wiring)
  - `strategy_engine/services.py` (`StrategyService` indicators + advanced performance engine)
  - `api/tests/` and `strategy_engine/tests/` (unit tests for API + engine)

## Non-Goals
- No new data sources; keep local CSV as default source of truth.
- No portfolio/multi-asset allocation; scope is single-asset backtest per request.
- No external TA dependencies required (e.g., avoid adding `pandas-ta` unless explicitly approved).
