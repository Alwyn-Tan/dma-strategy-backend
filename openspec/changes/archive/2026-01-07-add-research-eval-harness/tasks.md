## 1. Implementation
- [x] Add management command `research_eval` (argument parsing, run-id, output folder)
- [x] Implement fixed IS/OOS split evaluation with warm-up handling and strict isolation
- [x] Implement ablation variants (feature toggles mapped to advanced-mode params)
- [x] Implement annualized vol targeting input support (`target_vol_annual`, `trading_days_per_year`) end-to-end (views + service + meta)
- [x] Implement metric computation (MDD, Sharpe, Calmar, turnover, avg exposure)
- [x] Implement trade extraction for win rate and P/L ratio (trade list from fills)
- [x] Implement grid search on IS and locked evaluation on OOS; export heatmap data
- [x] Write reproducible artifacts to `results/research/<run_id>/`

## 2. Tests
- [x] Unit tests for annualization conversion and precedence rules
- [x] Unit tests for split boundaries and warm-up inclusion/exclusion
- [x] Unit tests for metrics (MDD/Sharpe/Calmar) on simple synthetic series
- [x] Unit tests for trade extraction and win rate / P/L ratio

## 3. Documentation
- [x] Add usage examples to `README.md` or `STARTUP_AND_TESTING.md`
