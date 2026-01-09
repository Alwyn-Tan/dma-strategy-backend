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
