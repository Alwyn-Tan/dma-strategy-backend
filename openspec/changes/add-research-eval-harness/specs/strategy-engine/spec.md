## ADDED Requirements

### Requirement: Annualized target volatility conversion
When provided with `target_vol_annual`, the system SHALL convert it to a daily target volatility using `trading_days_per_year`.

#### Scenario: Daily conversion uses sqrt rule
- **WHEN** `target_vol_annual=0.15` and `trading_days_per_year=252`
- **THEN** the daily target volatility equals `0.15 / sqrt(252)`

### Requirement: Consistent annualization for metrics
When producing annualized metrics (e.g., Sharpe, annualized return), the system SHALL use `trading_days_per_year` as the annualization basis.

#### Scenario: Sharpe annualization uses configured trading days
- **WHEN** the system computes Sharpe ratio
- **THEN** it annualizes using `sqrt(trading_days_per_year)`

## ADDED Requirements

### Requirement: OOS warm-up without leakage
For OOS evaluation, the system SHALL allow pre-OOS bars to be used only for indicator warm-up, while ensuring that decisions and reported OOS metrics use OOS bars only.

#### Scenario: OOS series starts at boundary date
- **WHEN** OOS start date is `2021-01-01`
- **THEN** the reported OOS equity series begins on `2021-01-01` (or first available bar on/after it)
- **AND** the strategy may use earlier bars only to compute indicator state at the boundary

