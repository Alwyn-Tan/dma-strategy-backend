# Design: Batch download to adjusted CSV

## Data Source
- Provider: `yfinance`
- Frequency: `1d`
- Price adjustment: **enabled** (use split/dividend-adjusted OHLC where available)

## Output Schema
CSV columns MUST be normalized to:
- `date` (YYYY-MM-DD)
- `open`
- `high`
- `low`
- `close`
- `volume`

No extra header rows; no multi-index columns.

## Output Directory
- Default output directory: project `data/` (i.e., `settings.DATA_DIR` default).
- The downloader SHOULD allow overriding the output directory for tests/dev runs, but the default is `data/`.

## Entrypoint
- The downloader SHALL be implemented as a Django management command (invoked via `python manage.py ...`).

## File Naming Rules
### Date-range mode
If the user provides `start_date` and/or `end_date`, the output filename SHALL include the explicit range:
- `CODE_<START>_<END>.csv`
  - `START` is `YYYY-MM-DD` if provided, otherwise `start` (literal)
  - `END` is `YYYY-MM-DD` if provided, otherwise `end` (literal)

Examples:
- `AAPL_2015-01-01_2025-12-31.csv`
- `SPY_2015-01-01_end.csv`
- `QQQ_start_2025-12-31.csv`

### Period mode
If neither `start_date` nor `end_date` is provided, the downloader SHALL use a `period` option and encode it in the filename:
- `CODE_<PERIOD>.csv`

Default period:
- `3y` (matches existing repo convention like `AAPL_3y.csv`)

Examples:
- `AAPL_3y.csv`
- `IWM_max.csv`

## Idempotency
- Re-running the downloader with the same inputs SHOULD produce the same filename and overwrite (atomically) or skip based on a `--force` flag.

## Observability
- For each symbol, log:
  - requested params (symbol, range/period)
  - row count written
  - min/max date actually returned
  - any error message on failure
