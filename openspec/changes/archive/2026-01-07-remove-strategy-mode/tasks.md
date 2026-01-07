## 1. Backend (API + engine)
- [x] Update query params: remove `strategy_mode`, add feature toggles and annualized vol targeting inputs
- [x] Refactor `StrategyService.calculate_performance` to use a unified code path with feature toggles
- [x] Ensure default behavior matches previous basic mode when all toggles are off
- [x] Update `meta.assumptions` output to include `features_enabled` and module params
- [x] Add/adjust tests for: default DMA, toggles validation, and a representative enabled-combination

## 2. Cross-Repo Prerequisites
- [x] Ensure `dma-frontend` merges its companion change `remove-strategy-mode` to stop sending `strategy_mode`
