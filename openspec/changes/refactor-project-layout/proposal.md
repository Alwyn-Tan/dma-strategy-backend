# Change: Refactor project layout into config/api/domain/tooling + pure Python modules

## Why
The current structure overloads a single Django app (`stocks/`) with responsibilities that are already diverging:
- HTTP/API (DRF views + query validation)
- Data access and ingestion (CSV parsing, optional yfinance refresh/write-back)
- Strategy engine (indicators, signals, backtest/performance logic)
- Future offline workflows (batch data download, research harness)

This makes future changes harder to implement cleanly—especially the pending OpenSpec changes:
- `add-yfinance-batch-csv` (offline data pipeline)
- `add-research-eval-harness` (offline research harness)

Refactoring into explicit modules (API vs domain models vs data vs strategy vs tooling) reduces coupling, clarifies ownership, and makes it easier to extend toward a DB-backed system (CSV remains a transitional data source).

## What Changes
- Rename the Django project package `dma_strategy/` → `config/` (settings/urls/asgi/wsgi).
- Replace the overloaded `stocks/` app with:
  - `api/` (Django app): DRF `urls/views/serializers` only (thin HTTP layer).
  - `domain/` (Django app): DB models/migrations/admin only (future DB path).
  - `tooling/` (Django app): management commands only (offline workflows).
- Extract non-Django business logic into pure Python packages:
  - `market_data/`: CSV IO/normalization, yfinance providers, naming rules.
  - `strategy_engine/`: indicators/signals/backtest/performance and shared utilities used by API and research.
- Keep public API routes and response shapes stable (`/api/codes/`, `/api/stock-data/`, `/api/signals/`).

## Impact
- Affected code:
  - `dma_strategy/*` → `config/*` (imports and settings module name change)
  - `stocks/*` split across `api/`, `domain/`, `tooling/`, `market_data/`, `strategy_engine/`
  - `pytest.ini` and tests updated for new settings module
- Affected OpenSpec changes:
  - `add-yfinance-batch-csv`: management command should live under `tooling/management/commands/` and call into `market_data/`.
  - `add-research-eval-harness`: management command should live under `tooling/management/commands/` and call into `strategy_engine/`.

## Non-Goals
- No new functionality or behavior changes in endpoints (beyond any unavoidable error message wording changes).
- No attempt to fully migrate CSV data into DB yet (CSV remains the MVP data source).
- No additional strategy logic changes (advanced/basic logic stays the same; only moved/refactored).

## Assumptions / Constraints
- Database is currently disposable (no production data); we can regenerate migrations and recreate the schema.
- Network access remains optional; `yfinance` usage stays inside offline tooling or explicitly gated flows.

## Open Questions
- App naming preference: `strategy_engine` vs `strategy`, `market_data` vs `datahub` (defaults above).
- Whether to keep a compatibility import layer (e.g., `stocks/` re-exports) temporarily to reduce churn, or do a clean cutover in one refactor PR.

