## 1. Implementation
- [x] Add a batch download management command entrypoint
- [x] Implement yfinance fetch with adjusted prices and normalized DataFrame schema
- [x] Implement naming rules for date-range mode and period mode
- [x] Write outputs to `data/` with atomic write (temp file then replace)
- [x] Add basic logging and per-symbol error handling (continue on error)

## 2. Tests
- [x] Unit tests for filename generation rules
- [x] Unit tests for DataFrame normalization (columns, date coercion, sorting)
- [x] Integration test with yfinance mocked (no network) verifying CSV write behavior

## 3. Documentation
- [x] Document usage and examples (README or STARTUP_AND_TESTING)
