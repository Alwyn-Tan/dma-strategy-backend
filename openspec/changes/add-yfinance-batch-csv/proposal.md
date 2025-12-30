# Change: Add batch yfinance downloader to normalized CSV (adjusted)

## Why
Strategy validation requires a diversified test universe across regimes and sectors. Manually preparing CSVs is slow and error-prone, and inconsistent data handling (splits/dividends, missing dates) can invalidate conclusions.

This change adds a repeatable data pipeline to bulk-download OHLCV from `yfinance`, **using adjusted prices**, and store the results under the project `data/` directory with predictable naming.

## What Changes
- Add a Django **management command** batch downloader that:
  - Fetches daily OHLCV from `yfinance` for a list of symbols
  - Uses **adjusted** prices (split/dividend-adjusted) to avoid structural breaks in price series
  - Normalizes to the backend CSV schema: `date,open,high,low,close,volume`
  - Writes files under `data/` using a deterministic naming convention (see design/spec)
- Keep the existing API behavior unchanged; this is an offline data preparation workflow.

## Impact
- Affected specs:
  - `market-data` (dataset creation + naming + schema)
- Affected code (expected):
  - New Django management command under `tooling/management/commands/`
  - Shared ingestion utilities under `market_data/`
  - Potential small updates to docs (`README.md`, `STARTUP_AND_TESTING.md`)

## Non-Goals (for this change)
- No parameter search / metric selection / ablation framework (will be proposed separately).
- No new storage backend (still local CSV under `data/`).
- No intraday timeframes (daily bars only).
