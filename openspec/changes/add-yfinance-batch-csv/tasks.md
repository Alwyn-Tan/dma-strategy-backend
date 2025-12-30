## 1. Implementation
- [ ] Add a batch download management command entrypoint
- [ ] Implement yfinance fetch with adjusted prices and normalized DataFrame schema
- [ ] Implement naming rules for date-range mode and period mode
- [ ] Write outputs to `data/` with atomic write (temp file then replace)
- [ ] Add basic logging and per-symbol error handling (continue on error)

## 2. Tests
- [ ] Unit tests for filename generation rules
- [ ] Unit tests for DataFrame normalization (columns, date coercion, sorting)
- [ ] Integration test with yfinance mocked (no network) verifying CSV write behavior

## 3. Documentation
- [ ] Document usage and examples (README or STARTUP_AND_TESTING)
