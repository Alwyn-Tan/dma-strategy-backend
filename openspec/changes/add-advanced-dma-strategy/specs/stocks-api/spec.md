## ADDED Requirements

### Requirement: Advanced strategy mode parameters
The system SHALL accept an optional `strategy_mode` query parameter on `GET /api/stock-data/` when `include_performance=true` to select between `basic` and `advanced` performance calculation.

#### Scenario: Default behavior remains basic
- **WHEN** the client calls `GET /api/stock-data/` with `include_performance=true` and without `strategy_mode`
- **THEN** the system returns `performance.strategy` and `performance.benchmark` using the current DMA buy/sell logic
- **AND** the response shape remains compatible with existing clients

#### Scenario: Advanced mode is opt-in
- **WHEN** the client calls `GET /api/stock-data/` with `include_performance=true&strategy_mode=advanced`
- **THEN** the system uses advanced-mode rules as defined by `strategy-engine`
- **AND** the system includes the advanced configuration under `meta.assumptions.strategy`

### Requirement: Advanced configuration query parameters
The system SHALL accept advanced-mode query parameters on `GET /api/stock-data/` and validate them with safe bounds.

#### Scenario: Valid advanced parameters are accepted
- **WHEN** the client supplies regime/ensemble/vol-target parameters within configured bounds
- **THEN** the system computes performance using those parameters

#### Scenario: Invalid advanced parameters are rejected
- **WHEN** the client supplies an invalid parameter value (e.g., negative window, malformed `ensemble_pairs`)
- **THEN** the system returns `400` with an error message describing the validation failure

### Requirement: Meta assumptions include strategy configuration
When `include_performance=true`, the system SHALL return `meta.assumptions` describing execution and strategy configuration sufficient to reproduce the run.

#### Scenario: Basic mode assumptions
- **WHEN** the client requests `include_performance=true` in basic mode
- **THEN** `meta.assumptions` includes fill model, fees/slippage, and signal rules (`confirm_bars`, `min_cross_gap`)

#### Scenario: Advanced mode assumptions
- **WHEN** the client requests `include_performance=true&strategy_mode=advanced`
- **THEN** `meta.assumptions.strategy` includes regime, ensemble, and volatility-target settings used

