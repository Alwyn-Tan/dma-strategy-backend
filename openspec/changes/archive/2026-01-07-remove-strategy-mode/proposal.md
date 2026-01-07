# Change: Remove `strategy_mode` and use explicit strategy feature toggles

## Why
The current API separates `basic` vs `advanced` via `strategy_mode`, which creates a “two strategies” mental model and makes incremental adoption awkward.
In practice, the strategy should be a single DMA baseline with optional modules (regime filter, ensemble, volatility targeting, exits) that the user explicitly enables.

## What Changes
- Remove the `strategy_mode` query parameter from the public contract for `/api/stock-data/` performance evaluation.
- Introduce explicit feature toggles (all default to `false`) so the default is pure DMA:
  - `use_ensemble` + `ensemble_pairs` (+ `ensemble_ma_type`)
  - `use_regime_filter` + `regime_ma_window` (+ optional `use_adx_filter`, `adx_window`, `adx_threshold`)
  - `use_vol_targeting` + `target_vol_annual` (+ `trading_days_per_year`, `vol_window`, `max_leverage`, `min_vol_floor`)
  - `use_chandelier_stop` + `chandelier_k`
  - `use_vol_stop` + `vol_stop_atr_mult`
- Update `meta.assumptions` to disclose enabled features and resolved effective parameters.

## Impact
- **BREAKING (API + UI)**: callers that depend on `strategy_mode=advanced` must migrate to feature toggles.
- Affected specs:
  - `stocks-api` (query params, validation, assumptions contract)
  - `strategy-engine` (how exposure is derived when features are enabled)
- Affected code (expected):
  - `stocks/views.py` (query validation, assumptions output)
  - `stocks/services.py` (remove branching by mode; unify engine with flags)
  - `dma-frontend/src/App.tsx` (remove Strategy Mode selector; add feature checkboxes and param panels)

## Migration
- Frontend will migrate immediately to toggles and stop sending `strategy_mode`.
- Backend behavior will be defined by toggles only; `strategy_mode` is removed from the contract.

