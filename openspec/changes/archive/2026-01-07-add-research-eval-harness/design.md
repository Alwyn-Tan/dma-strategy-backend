# Design: Research evaluation harness

## Entrypoint
- Implement as a Django management command (e.g., `python manage.py backtesting ...`).

## Data Inputs
- Source: local CSVs under `settings.DATA_DIR` (prepared by the data pipeline).
- Frequency: daily bars.
- Price adjustment: assumed already handled at ingestion (adjusted OHLCV CSVs).

## Core Evaluation Workflow
### Fixed split (MVP)
- Full data range target: `2015-01-01` to latest available.
- In-sample (IS): `2015-01-01` to `2020-12-31`
- Out-of-sample (OOS): `2021-01-01` to latest

### Isolation rules
- Parameter selection MUST use IS only.
- OOS data MUST NOT be used for any optimization, threshold tuning, or model selection.
- **Warm-up rule**: OOS performance may use pre-2021 history ONLY to compute indicators at the OOS boundary (e.g., MA200/ATR/ADX), but decisions and evaluation metrics for OOS MUST be computed strictly on bars whose dates are within OOS.

## Volatility Targeting Annualization
- User-facing input: `target_vol_annual` (decimal; `0.15` means 15% annualized).
- Convert internally:
  - `target_vol_daily = target_vol_annual / sqrt(trading_days_per_year)`
- Default: `trading_days_per_year = 252`.
- Volatility proxy in the engine remains `ATR(window) / close` unless a future method is added.

### Precedence
If both are provided:
- Prefer `target_vol_annual` + `trading_days_per_year` conversion.
- `target_vol` (daily) remains supported for backward compatibility.

## Metrics
### Survival & risk-adjusted
- Max drawdown (MDD)
- Sharpe ratio (annualized, consistent with `trading_days_per_year`)
- Calmar ratio (`annualized_return / MDD`)

### Behavior
- Win rate (trade-level)
- Profit/Loss ratio (avg win / avg loss)
- Turnover (annualized; or proxy via traded notional / avg equity)
- Average exposure (mean of target exposure; advanced mode)

## Outputs (reproducible artifacts)
Write under `results/backtesting/<run_id>/`:
- `config.json` (symbols, costs, split dates, parameter grids, objective, annualization basis)
- `summary.csv` (per symbol, per variant: metrics for IS and OOS)
- `series/` folder:
  - `CODE_variant_is.json` and `CODE_variant_oos.json` (equity curves and benchmark)
- `heatmaps/` folder (data-only):
  - `CODE_is_heatmap.json` for parameter sensitivity (no plotting dependency required)

## Variants (ablation)
The harness SHOULD support a variant matrix, e.g.:
- `basic`
- `advanced_full`
- `advanced_no_regime`
- `advanced_no_adx`
- `advanced_no_vol_targeting`
- `advanced_no_exits`

## Search strategy (grid search MVP)
- Use a bounded grid with constraints (e.g., `short < long`).
- Optimize on IS only.
- Lock best parameters and evaluate on OOS.
- Include a plateau/sensitivity view by exporting heatmap-ready data.
