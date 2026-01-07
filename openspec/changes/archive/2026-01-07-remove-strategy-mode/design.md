# Design: Unified strategy with optional modules

## Baseline
Default behavior (no feature toggles enabled) SHALL be pure DMA:
- Signal: `ma_short` vs `ma_long` cross (existing `short_window`, `long_window`)
- Position: binary (0% or 100% exposure)
- Execution: next-day open (existing research assumption)

## Feature toggles (explicit)
All feature toggles default to `false`. A feature is applied only when its toggle is `true`.

### Ensemble
- Enable with `use_ensemble=true`
- Required: `ensemble_pairs` (e.g. `5:20,10:50,20:100,50:200`)
- Optional: `ensemble_ma_type` (`sma`/`ema`)
- Behavior: produce `target_exposure` in `[0, 1]` as the fraction of pairs in “long” state.

### Regime filter
- Enable with `use_regime_filter=true`
- Parameter: `regime_ma_window` (default 200)
- Behavior: force `target_exposure=0` when `close <= MA(regime_ma_window)`.
- Optional ADX gate:
  - Enable with `use_adx_filter=true` (only meaningful if `use_regime_filter=true`)
  - Parameters: `adx_window` (default 14), `adx_threshold` (default 20)
  - Behavior: force `target_exposure=0` when `ADX <= threshold`

### Volatility targeting
- Enable with `use_vol_targeting=true`
- User input: `target_vol_annual` (decimal), `trading_days_per_year` (default 252)
- Convert internally: `target_vol_daily = target_vol_annual / sqrt(trading_days_per_year)`
- Vol proxy: `atr_pct = ATR(vol_window)/close` (current implementation); scaling: `min(max_leverage, target_vol_daily/atr_pct)`
- Guardrails: `min_vol_floor`, leverage caps.

### Exits
- `use_chandelier_stop=true` uses `chandelier_k * ATR` trailing stop.
- `use_vol_stop=true` uses `vol_stop_atr_mult * ATR` hard stop from entry.
- Stop evaluation MUST avoid lookahead (stop level derived from info up to `t-1`).

## Meta assumptions
When `include_performance=true`, `meta.assumptions.strategy` SHALL include:
- `features_enabled` object (booleans)
- each module’s parameters actually used (including annualization basis).

