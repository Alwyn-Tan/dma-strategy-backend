## MODIFIED Requirements

### Requirement: Annualized volatility targeting inputs
When `use_vol_targeting=true`, the system SHALL accept:
- `target_vol_annual` (decimal)
- `trading_days_per_year` (default 252)
- `target_vol` (legacy daily target volatility, decimal)

#### Scenario: Annualized target vol is accepted
- **WHEN** the client calls `/api/stock-data/` with `include_performance=true&use_vol_targeting=true&target_vol_annual=0.15`
- **THEN** the system uses `target_vol_annual` to compute a daily target volatility internally

#### Scenario: Trading days default
- **WHEN** the client supplies `target_vol_annual` without `trading_days_per_year`
- **THEN** the system defaults `trading_days_per_year` to `252`

#### Scenario: Legacy daily target vol remains supported
- **WHEN** the client calls `/api/stock-data/` with `include_performance=true&use_vol_targeting=true&target_vol=0.02`
- **THEN** the system computes performance using the provided daily target volatility

#### Scenario: Annualized overrides daily
- **WHEN** both `target_vol_annual` and `target_vol` are present
- **THEN** the system prefers `target_vol_annual` as the source of truth
