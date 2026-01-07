## 1. Implementation
- [x] Add API params for `strategy_mode` and advanced options (regime/ensemble/vol targeting/stops) with safe defaults
- [x] Implement indicator helpers in `StrategyService` (ATR, ADX, EMA option if needed)
- [x] Implement signal ensembling to produce daily `target_exposure` in `[0, 1]`
- [x] Implement volatility targeting to scale exposure by current volatility and caps (`max_leverage`, min/max exposure)
- [x] Extend performance engine to support fractional exposure and optional ATR-based exits without lookahead
- [x] Extend `meta.assumptions` to include advanced configuration and derived execution assumptions

## 2. Tests
- [x] Unit tests for ATR and ADX calculations (shape, NaN handling, simple sanity checks)
- [x] Unit tests for ensembling logic and exposure mapping
- [x] Unit tests for volatility targeting scaling and leverage caps
- [x] Regression test: `strategy_mode=basic` matches current output shape/behavior
- [x] API test: `include_performance=true&strategy_mode=advanced` returns expected keys and `meta.assumptions`

## 3. Documentation
- [x] Update `README.md` (or API docs) with advanced-mode parameters and examples
