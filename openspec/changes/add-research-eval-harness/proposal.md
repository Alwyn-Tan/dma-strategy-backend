# Change: Add research evaluation harness (ablation + IS/OOS + parameter search)

## Why
After upgrading the strategy to an advanced structure (filters, ensembling, volatility targeting, exits), we need a rigorous, repeatable research workflow to:
- Verify each module contributes real robustness (via ablation)
- Prevent overfitting (via strict IS/OOS isolation)
- Report risk-adjusted and “pain” metrics in a consistent annualization basis

## What Changes
- Add an offline **research evaluation harness** (Django management command) that can:
  - Run baseline vs advanced vs ablations across a symbol pool
  - Perform fixed-split IS/OOS evaluation with strict isolation rules
  - Run constrained grid search on the IS period and evaluate locked parameters on OOS
  - Output reproducible artifacts (config + metrics + series) under `results/`
- Extend advanced strategy inputs to accept **annualized volatility targeting** parameters:
  - `target_vol_annual` (e.g., `0.15` for 15%)
  - `trading_days_per_year` (default `252`) for annualization conversions
  - Keep compatibility with existing daily `target_vol` (legacy) by defining precedence rules

## Impact
- Affected specs:
  - `research-evaluation` (harness workflow + outputs)
  - `stocks-api` (new query params for annualized vol target in advanced mode)
  - `strategy-engine` (annualization and volatility-targeting semantics)
- Affected code (expected):
  - New management command under `tooling/management/commands/`
  - `strategy_engine/services.py` advanced mode parameter handling (annualization support)
  - `api/serializers.py` and `api/views.py` query validation and `meta.assumptions` output

## Non-Goals (for this change)
- No walk-forward analysis (WFA) / Monte Carlo yet (planned follow-up).
- No new data source (data prep remains in separate pipeline change).
- No new frontend UI requirements.
