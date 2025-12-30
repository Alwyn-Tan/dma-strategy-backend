## 1. Implementation
- [ ] Add management command `research_eval` (argument parsing, run-id, output folder)
- [ ] Implement fixed IS/OOS split evaluation with warm-up handling and strict isolation
- [ ] Implement ablation variants (feature toggles mapped to advanced-mode params)
- [ ] Implement annualized vol targeting input support (`target_vol_annual`, `trading_days_per_year`) end-to-end (views + service + meta)
- [ ] Implement metric computation (MDD, Sharpe, Calmar, turnover, avg exposure)
- [ ] Implement trade extraction for win rate and P/L ratio (trade list from fills)
- [ ] Implement grid search on IS and locked evaluation on OOS; export heatmap data
- [ ] Write reproducible artifacts to `results/research/<run_id>/`

## 2. Tests
- [ ] Unit tests for annualization conversion and precedence rules
- [ ] Unit tests for split boundaries and warm-up inclusion/exclusion
- [ ] Unit tests for metrics (MDD/Sharpe/Calmar) on simple synthetic series
- [ ] Unit tests for trade extraction and win rate / P/L ratio

## 3. Documentation
- [ ] Add usage examples to `README.md` or `STARTUP_AND_TESTING.md`

