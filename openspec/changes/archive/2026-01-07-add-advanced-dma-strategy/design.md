# Design: Advanced DMA strategy structure

## Goals
- Improve robustness vs. choppy markets and volatility spikes without changing the data model.
- Preserve existing default behavior and API shapes.
- Avoid lookahead bias: decisions at bar `t` execute no earlier than bar `t+1` open (consistent with current assumptions).

## Definitions
- **Regime filter**: a gating rule that disables long exposure unless a higher-timeframe condition is true.
  - Default candidate: `close > SMA(regime_ma_window=200)`
  - Optional: require `ADX(adx_window=14) > adx_threshold (20/25)`
- **Ensemble**: compute multiple trend signals from different MA pairs and average them.
  - Example MA pairs: `(5,20),(10,50),(20,100),(50,200)`
  - Map each pair to a discrete signal in `{0,1}` (long/flat) or `{-1,0,1}` (if shorting is later enabled).
  - `trend_score = mean(pair_signals)` → `target_exposure = clip(trend_score, 0, 1)`
- **Volatility targeting**: scale exposure inversely to current volatility.
  - Use a volatility proxy such as `ATR(window)/close` (dimensionless) or returns EWMA vol.
  - Example: `scaled_exposure = target_exposure * min(max_leverage, target_vol / current_vol)`
  - Apply guardrails: min data requirements, floor on `current_vol` to avoid division spikes, and caps.

## Performance engine changes (conceptual)
- Replace binary “all-in buy / all-out sell” with daily exposure-aware equity updates:
  - Compute desired exposure for day `t` from indicators on `t` (close-based) and execute at `t+1` open.
  - Maintain cash + shares; adjust to match desired exposure at each rebalance step.
- Optional exits (when enabled):
  - **Chandelier stop**: after entry, track `High_max` and set `stop = High_max - k * ATR`.
  - **Volatility stop**: force exit if drawdown from entry exceeds `m * ATR`.
  - Stops trigger intraday using `low`/`high`, but execution must remain conservative (e.g., stop price or next open).

## Parameters (initial proposal)
- `strategy_mode`: `basic` (default) | `advanced`
- Regime:
  - `regime_ma_window` (default 200)
  - `use_adx_filter` (default false), `adx_window` (default 14), `adx_threshold` (default 20)
- Ensemble:
  - `ensemble_pairs` (CSV string, e.g. `5:20,10:50,20:100,50:200`)
  - `ensemble_ma_type` (default `sma`, optional `ema`)
- Vol targeting:
  - `target_vol` (e.g., daily volatility target in decimal, or annualized if explicitly specified)
  - `vol_window` (default 14 if ATR-based)
  - `max_leverage` (default 1.0), `min_vol_floor`
- Exits (optional):
  - `use_chandelier_stop`, `chandelier_k` (2–3)
  - `use_vol_stop`, `vol_stop_atr_mult` (e.g., 2)

## Compatibility
- `basic` mode must remain the default and match current semantics and output keys.
- Advanced mode may add new keys to `performance` and `signals` payloads, but MUST retain existing keys.

