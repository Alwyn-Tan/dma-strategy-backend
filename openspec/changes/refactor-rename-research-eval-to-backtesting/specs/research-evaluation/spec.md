## MODIFIED Requirements

### Requirement: Research evaluation management command
The system SHALL provide a Django management command `backtesting` to run research evaluations across a list of symbols and output reproducible artifacts to `results/`.

#### Scenario: Run evaluation across a pool
- **WHEN** the user runs `python manage.py backtesting --symbols ...`
- **THEN** the system produces per-symbol results for all configured variants
- **AND** writes outputs to a new `results/backtesting/<run_id>/` directory

