## MODIFIED Requirements

### Requirement: Performance query parameters
The system SHALL compute performance for `GET /api/stock-data/` when `include_performance=true` using a unified DMA-based strategy with optional modules enabled by explicit feature toggles.

#### Scenario: Default is pure DMA
- **WHEN** the client calls `/api/stock-data/` with `include_performance=true` and does not enable any feature toggles
- **THEN** the system computes performance using pure DMA rules (binary exposure based on MA cross)

#### Scenario: Modules are opt-in via toggles
- **WHEN** the client enables a module toggle (e.g., `use_regime_filter=true`)
- **THEN** the system applies that module’s logic using the provided parameters (or documented defaults)

## REMOVED Requirements

### Requirement: Strategy mode selection
The system previously accepted `strategy_mode=basic|advanced` to select performance calculation behavior.

#### Scenario: Strategy mode removed
- **WHEN** the client attempts to rely on `strategy_mode`
- **THEN** the public contract does not require or document `strategy_mode` for determining behavior

## ADDED Requirements

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

#### Scenario: Annualized conversion is used
- **WHEN** `use_vol_targeting=true&target_vol_annual=0.15`
- **THEN** the system uses annualized-to-daily conversion internally and discloses it in `meta.assumptions`

### Requirement: Meta assumptions disclose enabled features
When `include_performance=true`, the system SHALL return `meta.assumptions.strategy.features_enabled` and module parameters actually used.

#### Scenario: Assumptions include feature toggles
- **WHEN** the response includes performance
- **THEN** `meta.assumptions.strategy.features_enabled` is present and reflects the toggles used

