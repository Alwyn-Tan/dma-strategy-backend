## 1. Implementation
- [x] Create `config/` package from `dma_strategy/` and update settings module references
- [x] Create Django apps `api/`, `domain/`, `tooling/` and register them in `INSTALLED_APPS`
- [x] Split `stocks/views.py` into `api/views.py` + `api/serializers.py`, keep routes stable
- [x] Move `stocks/models.py` (and admin registration) into `domain/`
- [x] Split `stocks/services.py` into `market_data/` (CSV + yfinance + naming) and `strategy_engine/` (indicators/signals/backtest)
- [x] Remove `stocks/` and update all imports/usages
- [x] Rebuild migrations for `domain/` (DB is disposable)

## 2. Tests
- [x] Update pytest config (`pytest.ini`) and fix imports after move
- [ ] Keep existing API and services tests passing with new module boundaries
- [ ] Add/adjust minimal tests to ensure the “public API routes unchanged” contract holds

## 3. Documentation
- [x] Update `README.md` directory structure section
- [x] Update `STARTUP_AND_TESTING.md` if commands/paths change

## 4. OpenSpec coordination
- [x] Update pending change docs to reference new command/module locations:
  - [x] `openspec/changes/add-yfinance-batch-csv/*`
  - [x] `openspec/changes/add-research-eval-harness/*`
