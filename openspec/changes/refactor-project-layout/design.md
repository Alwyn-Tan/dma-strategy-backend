# Design: Target structure and module responsibilities

## Target repository layout (high level)

```text
dma-strategy-backend/
├── manage.py
├── config/                 # Django project package (settings/urls/asgi/wsgi)
├── api/                    # Django app (DRF HTTP layer)
├── domain/                 # Django app (DB models/admin/migrations)
├── tooling/                # Django app (management commands only)
├── market_data/            # Pure Python package (CSV/yfinance + normalization + naming)
└── strategy_engine/        # Pure Python package (indicators/signals/backtest/perf/metrics)
```

## Responsibilities and boundaries

### `config/` (Django project package)
- Owns: environment loading, settings, global middleware, root URL routing.
- Does not own: any domain logic, IO, or strategy logic.

### `api/` (Django app)
- Owns: request parsing/validation and response shaping for `/api/*`.
- Calls into:
  - `market_data` for data retrieval (CSV + refresh decisioning where applicable)
  - `strategy_engine` for MA/signal/performance outputs
- Avoids: file IO and pandas-heavy logic inside views.

### `domain/` (Django app)
- Owns: DB models + migrations (future source of truth).
- For the refactor: models may remain unused by the MVP path, but must be preserved as the DB landing zone.

### `tooling/` (Django app)
- Owns: management commands only.
- Commands should be thin orchestration layers:
  - parse args
  - call `market_data` and/or `strategy_engine`
  - write artifacts (`data/`, `results/`)

### `market_data/` (pure Python)
- Owns:
  - CSV schema normalization: `date,open,high,low,close,volume`
  - Atomic write patterns (temp then replace)
  - Naming rules (period mode and date-range mode)
  - Data source adapters/providers (yfinance)
- Does not own: indicators, signals, performance evaluation.

### `strategy_engine/` (pure Python)
- Owns:
  - indicators (MA/ATR/ADX)
  - signal generation (basic crossover)
  - backtest / performance series (basic + advanced)
  - shared utilities needed by research harness (metrics, trade extraction) when implemented
- Does not own: file IO, Django request/response objects.

## Django wiring changes
- `manage.py` uses `DJANGO_SETTINGS_MODULE=config.settings`.
- `pytest.ini` uses `DJANGO_SETTINGS_MODULE=config.settings`.
- `config/urls.py` mounts `api/urls.py` under `/api/`.
- `INSTALLED_APPS` includes `api`, `domain`, `tooling`, plus DRF/CORS and Django defaults.

## Database / migrations approach (disposable DB)
- Since DB is empty/disposable, we can:
  - delete legacy `stocks` migrations and app
  - create fresh `domain` app migrations (`0001_initial.py`)
  - recreate DB via `python manage.py migrate`

## Alignment with pending changes

### `add-yfinance-batch-csv`
- Command: `tooling.management.commands.yfinance_batch_download`
- Core logic: `market_data.providers.yfinance` + `market_data.csv_io` + `market_data.naming`

### `add-research-eval-harness`
- Command: `tooling.management.commands.backtesting`
- Core logic: `strategy_engine.*` and writes under `results/`
