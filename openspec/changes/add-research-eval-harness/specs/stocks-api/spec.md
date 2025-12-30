## ADDED Requirements

### Requirement: Annualized volatility targeting parameters (advanced mode)
When `strategy_mode=advanced`, the system SHALL accept `target_vol_annual` and `trading_days_per_year` query parameters on `GET /api/stock-data/` when `include_performance=true`.

#### Scenario: Annualized target vol is accepted
- **WHEN** the client calls `/api/stock-data/` with `include_performance=true&strategy_mode=advanced&target_vol_annual=0.15`
- **THEN** the system uses `target_vol_annual` to compute a daily target volatility internally

#### Scenario: Trading days default
- **WHEN** the client supplies `target_vol_annual` without `trading_days_per_year`
- **THEN** the system defaults `trading_days_per_year` to `252`

### Requirement: Backward compatibility for daily target vol
The system SHALL continue to accept the legacy daily `target_vol` parameter in advanced mode.

#### Scenario: Legacy parameter remains supported
- **WHEN** the client calls `/api/stock-data/` with `include_performance=true&strategy_mode=advanced&target_vol=0.02`
- **THEN** the system computes performance using the provided daily target volatility

### Requirement: Parameter precedence
If `target_vol_annual` and `target_vol` are both provided, the system SHALL prefer `target_vol_annual`.

#### Scenario: Annualized overrides daily
- **WHEN** both `target_vol_annual` and `target_vol` are present
- **THEN** the system uses `target_vol_annual` as the source of truth

### Requirement: Meta assumptions disclose annualization basis
When `include_performance=true&strategy_mode=advanced`, the system SHALL include `target_vol_annual` (when used) and `trading_days_per_year` in `meta.assumptions.strategy.vol_targeting`.

#### Scenario: Assumptions include annualization fields
- **WHEN** the client requests advanced performance using annualized vol targeting
- **THEN** the response includes the annualization configuration in `meta.assumptions`

