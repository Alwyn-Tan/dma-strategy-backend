## ADDED Requirements

### Requirement: Batch download daily bars from yfinance
The system SHALL provide a Django management command to download daily OHLCV bars from `yfinance` for a list of symbols and write them as CSV files under the project `data/` directory.

#### Scenario: Download a list of symbols
- **WHEN** the user runs the batch downloader for symbols `SPY,QQQ,IWM`
- **THEN** the system downloads daily bars from `yfinance` for each symbol
- **AND** writes one CSV per symbol under `data/`
- **AND** continues processing remaining symbols if one symbol fails

### Requirement: Use adjusted prices
The system SHALL download and output **adjusted** OHLCV series to reduce distortions caused by splits and dividends.

#### Scenario: Split-adjusted output
- **WHEN** the underlying asset has a split/dividend adjustment in the requested range
- **THEN** the output OHLC series reflects adjusted prices (no discontinuity from the corporate action)

### Requirement: Normalize CSV schema
The system SHALL normalize downloaded data to CSV schema `date,open,high,low,close,volume`.

#### Scenario: Normalized output columns
- **WHEN** the downloader writes a CSV file
- **THEN** the first row contains the header `date,open,high,low,close,volume`
- **AND** all rows are sorted ascending by `date`

### Requirement: Deterministic naming for date ranges
When `start_date` and/or `end_date` are provided, the system SHALL name the output file as `CODE_<START>_<END>.csv` where missing bounds are encoded as `start`/`end`.

#### Scenario: Both bounds provided
- **WHEN** the user requests `code=AAPL` from `2015-01-01` to `2025-12-31`
- **THEN** the output filename is `AAPL_2015-01-01_2025-12-31.csv`

#### Scenario: Open-ended bounds
- **WHEN** the user requests `code=SPY` from `2015-01-01` with no end date
- **THEN** the output filename is `SPY_2015-01-01_end.csv`

### Requirement: Deterministic naming for period downloads
When neither `start_date` nor `end_date` is provided, the system SHALL name the output file as `CODE_<PERIOD>.csv` and default to `PERIOD=3y`.

#### Scenario: Default period
- **WHEN** the user downloads `KO` with no date bounds
- **THEN** the output filename is `KO_3y.csv`
