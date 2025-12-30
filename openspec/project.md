# Project Context

## Purpose
`dma-strategy-backend` is a Django + DRF backend for a dual moving average (DMA) strategy MVP.

Primary goals:
- Serve stock OHLCV data from local CSV files (`DATA_DIR`)
- Compute moving averages (`ma_short`, `ma_long`) and generate BUY/SELL signals
- Support an optional “auto-refresh on request” path to extend local CSV data via `yfinance`
- Provide endpoints tailored for a frontend UI (including optional `meta` + response headers)

## Tech Stack
- Python 3.10+
- Django 5.x (`config/`)
- Django REST framework (DRF) for API views/serialization
- pandas + numpy for time series calculation
- `python-dotenv` (`load_dotenv()` in `config/settings.py`)
- Testing: `pytest`, `pytest-django` (`pytest.ini` sets `DJANGO_SETTINGS_MODULE`)
- CORS: `django-cors-headers`

Optional / “future-ready” components (enabled by env vars / configuration):
- Data refresh source: `yfinance`
- Database: SQLite (default), PostgreSQL when `DB_ENGINE=postgres`
- Cache: local memory (default), Redis when `CACHE_BACKEND=redis`
- Auth: `djangorestframework-simplejwt` (not required for MVP; current default permissions allow anonymous)
- Background jobs: Celery (present in deps; not required for MVP)

## Project Conventions

### Code Style
- Keep views thin and put domain logic in:
  - `market_data/services.py` (`StockDataService`)
  - `strategy_engine/services.py` (`StrategyService`)
- Prefer explicit types and clear naming (snake_case, type hints like `list[dict]`, `Optional[date]`).
- Validate query parameters using DRF serializers in `api/serializers.py`:
  - `StockQuerySerializer` for `/api/stock-data/`
  - `SignalsQuerySerializer` for `/api/signals/`
- API query params use snake_case (e.g., `short_window`, `long_window`, `include_meta`, `force_refresh`).
- Ensure JSON output contains no `NaN`/`Infinity` (pandas rolling produces `NaN`); current pattern converts to `None` before rendering.

### Architecture Patterns
**Django app layout**
- Project config: `config/` (settings/urls/asgi/wsgi)
- API app: `api/` (views/serializers/urls)
- Domain/DB app: `domain/` (models/migrations/admin)
- Tooling app: `tooling/` (management commands)
- Pure Python modules: `market_data/`, `strategy_engine/`

**Data access (MVP)**
- Local CSV is the primary data source (`settings.DATA_DIR`, default `./data`).
- File resolution favors `data/<CODE>.csv`, `data/<CODE>_3y.csv` and case variants.
- Stock codes are sanitized (allow only `A-Za-z0-9._-`) to avoid path traversal and ambiguous filenames.
- CSV parsing supports both:
  - “simple” format: `date,open,high,low,close,volume`
  - repo-style format with extra “Ticker/Date” rows (skipped when needed)

**Optional auto refresh**
- If enabled (`AUTO_REFRESH_ON_REQUEST=true`), requests with a date range not covered by local CSV may fetch missing rows from `yfinance` and merge/write back to the CSV.
- Refresh is rate-limited via cache key `stock_refresh:<CODE>` using `AUTO_REFRESH_COOLDOWN_SECONDS`.

**API surface**
- Routes live under `/api/` via `config/urls.py` → `api/urls.py`.
- Key endpoints:
  - `GET /api/codes/`: list available codes derived from CSV filenames
  - `GET /api/stock-data/`: return OHLCV + MAs; supports optional `include_meta`, `include_performance`
  - `GET /api/signals/`: return `{ data, meta }` with generated and filtered signals

**Meta + headers**
- When `include_meta=true`, `/api/stock-data/` returns `{ data, meta }` and also adds headers like `X-Data-Status`, `X-Data-Range`, `X-Data-Last-Updated`, `X-Data-Refresh`, `X-Data-Refresh-Reason`.

**Configuration (env vars)**
- Loaded from `.env` via `load_dotenv()` in `config/settings.py`.
- Common:
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - `DATA_DIR` (CSV directory), `LOG_LEVEL`
- Auto refresh:
  - `AUTO_REFRESH_ON_REQUEST` (default true), `AUTO_REFRESH_COOLDOWN_SECONDS` (default 3600)
- Optional infra toggles:
  - `DB_ENGINE=sqlite|postgres` and `DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT`
  - `CACHE_BACKEND=locmem|redis` and `REDIS_URL`

### Testing Strategy
- Use `pytest` + `pytest-django` (see `pytest.ini`).
- Prefer deterministic unit tests around:
  - CSV parsing / date filtering (`StockDataService`)
  - MA calculation, signal generation, performance curves (`StrategyService`)
- API tests use the Django test client (see `api/tests/test_api.py`).
- Avoid network in tests; if touching auto-refresh, mock out `yfinance`.

### Git Workflow
- No strict workflow enforced in-repo; prefer small, focused commits and PRs.
- Keep docs, specs (`openspec/`), and code changes in the same PR when they belong together.

### Cross-Repo Changes
This project is commonly developed alongside `dma-frontend` (separate repo). When a requirement spans frontend + backend, treat it as a coordinated change across two OpenSpec spaces.

Rules:
- Use the same `change-id` in both repos (e.g., `add-benchmark-performance`).
- Create a change folder in both repos:
  - `dma-strategy-backend/openspec/changes/<change-id>/...`
  - `dma-frontend/openspec/changes/<change-id>/...`
- Pick a “lead” repo for the proposal:
  - Backend-led when API shape/behavior changes.
  - Frontend-led when UI/UX changes without API changes.
- In the lead repo `proposal.md`, document the end-to-end contract (API request/response shapes, error cases, UI behaviors).
- In the companion repo `proposal.md`, keep it short and link to the lead proposal; focus on repo-specific impact only.
- Keep tasks repo-local: `tasks.md` in each repo should only include work that repo owns, plus explicit cross-repo prerequisites (e.g., “merge backend first”).
- Validate in both repos before review: `openspec validate <change-id> --strict`.

API contract convention:
- Treat backend as the canonical source for API contracts/specs; frontend proposals should link to the backend contract sections (and mirror types in `src/api/types.ts` only as implementation detail).

## Domain Context
- Strategy: dual moving average cross (short vs long).
  - BUY when `ma_short` crosses above `ma_long`
  - SELL when `ma_short` crosses below `ma_long`
- Signal generation parameters:
  - `gen_confirm_bars`: require the MA spread to stay on the crossed side for N bars (signal date becomes the confirmation bar)
  - `gen_min_cross_gap`: minimum gap (in bars) between same-type signals
- Performance / benchmark (research mode, optional via `include_performance=true`):
  - Compare strategy equity curve vs buy-and-hold benchmark
  - Execution assumption: trade on next day open to avoid lookahead
  - Output is normalized (start value = `1.0`) and aligned to the filtered date series

## Important Constraints
- MVP must work without PostgreSQL/Redis/Celery/JWT (local CSV-only path should be the default happy path).
- `yfinance` refresh requires network access and should be treated as optional in dev/CI.
- Date handling is day-level (`date`), with project timezone set to `Asia/Hong_Kong` in `config/settings.py`.
- `DATA_DIR` must be configurable and should be treated as trusted local storage; do not allow arbitrary file reads outside it.

## External Dependencies
- External market data (optional): `yfinance` (Yahoo Finance) for on-demand refresh.
- Optional infrastructure:
  - PostgreSQL (when enabled via env vars)
  - Redis (cache backend when enabled)
