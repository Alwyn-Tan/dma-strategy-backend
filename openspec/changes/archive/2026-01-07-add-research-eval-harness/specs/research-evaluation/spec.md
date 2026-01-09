## ADDED Requirements

### Requirement: Research evaluation management command
The system SHALL provide a Django management command to run research evaluations across a list of symbols and output reproducible artifacts to `results/`.

#### Scenario: Run evaluation across a pool
- **WHEN** the user runs the command for a pool of symbols
- **THEN** the system produces per-symbol results for all configured variants
- **AND** writes outputs to a new `results/research/<run_id>/` directory

### Requirement: Fixed IS/OOS split evaluation
The evaluation harness SHALL support a fixed split with IS `2015-01-01..2020-12-31` and OOS `2021-01-01..latest` by default.

#### Scenario: Strict IS optimization and OOS evaluation
- **WHEN** the user enables parameter search
- **THEN** the harness selects parameters using IS only
- **AND** evaluates the selected parameters on OOS without further tuning

### Requirement: Ablation variants
The evaluation harness SHALL support ablation variants to isolate the contribution of strategy modules.

#### Scenario: Compare full vs ablated
- **WHEN** the user runs `advanced_full` and `advanced_no_vol_targeting`
- **THEN** the harness reports metrics for both variants on IS and OOS for comparison

### Requirement: Metrics output
The evaluation harness SHALL compute and export a metrics table including, at minimum:
MDD, Sharpe, Calmar, turnover, win rate, and profit/loss ratio.

#### Scenario: Export summary CSV
- **WHEN** the evaluation completes
- **THEN** the harness writes `summary.csv` with per-symbol, per-variant metrics for IS and OOS

