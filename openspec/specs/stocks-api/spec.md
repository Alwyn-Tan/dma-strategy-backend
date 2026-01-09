# stocks-api Specification

## Purpose
TBD - created by archiving change add-advanced-dma-strategy. Update Purpose after archive.
## Requirements
### Requirement: Advanced configuration query parameters
The system SHALL accept module parameters for enabled features on `GET /api/stock-data/` and validate them with safe bounds.

#### Scenario: Valid module parameters are accepted
- **WHEN** the client supplies regime/ensemble/vol-target parameters within configured bounds
- **THEN** the system computes performance using those parameters

#### Scenario: Invalid module parameters are rejected
- **WHEN** the client supplies an invalid parameter value (e.g., negative window, malformed `ensemble_pairs`)
- **THEN** the system returns `400` with an error message describing the validation failure

### Requirement: Performance query parameters
The system SHALL compute performance for `GET /api/stock-data/` when `include_performance=true` using a unified DMA-based strategy with optional modules enabled by explicit feature toggles.

#### Scenario: Default is pure DMA
- **WHEN** the client calls `/api/stock-data/` with `include_performance=true` and does not enable any feature toggles
- **THEN** the system computes performance using pure DMA rules (binary exposure based on MA cross)

#### Scenario: Modules are opt-in via toggles
- **WHEN** the client enables a module toggle (e.g., `use_regime_filter=true`)
- **THEN** the system applies that module’s logic using the provided parameters (or documented defaults)

#### Scenario: Strategy mode does not affect behavior
- **WHEN** the client supplies `strategy_mode` in the query string
- **THEN** behavior is determined by feature toggles only (and `strategy_mode` does not change results)

### Requirement: Meta assumptions disclose enabled features
When `include_performance=true`, the system SHALL return `meta.assumptions` describing execution and strategy configuration sufficient to reproduce the run, including enabled features and effective parameters.

#### Scenario: Assumptions include feature toggles
- **WHEN** the response includes performance
- **THEN** `meta.assumptions.strategy.features_enabled` is present and reflects the toggles used

#### Scenario: Annualized vol targeting is disclosed
- **WHEN** `use_vol_targeting=true` and the server computes any annualized-to-daily conversion
- **THEN** the conversion inputs/assumptions are disclosed under `meta.assumptions.strategy.vol_targeting`

### Requirement: Feature toggle parameters
The system SHALL accept the following feature toggles (all default `false`) when `include_performance=true`:
- `use_ensemble`
- `use_regime_filter`
- `use_adx_filter`
- `use_vol_targeting`
- `use_chandelier_stop`
- `use_vol_stop`

#### Scenario: Disabled toggles do not affect behavior
- **WHEN** a toggle is `false`
- **THEN** the system does not apply that module, regardless of other module parameters present

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

