## ADDED Requirements

### Requirement: Unified exposure derivation
The system SHALL derive daily target exposure from DMA and optional modules enabled via explicit toggles, without using a `basic/advanced` mode switch.

#### Scenario: Pure DMA exposure
- **WHEN** all toggles are disabled
- **THEN** exposure is binary based on the configured DMA signal

#### Scenario: Ensemble produces fractional exposure
- **WHEN** `use_ensemble=true`
- **THEN** exposure MAY be fractional in `[0, 1]` based on ensemble agreement

### Requirement: OOS warm-up without leakage
When evaluating OOS segments, the system SHALL allow pre-OOS history only for indicator warm-up while ensuring reported OOS series and metrics only use OOS bars.

#### Scenario: Warm-up does not change OOS boundary
- **WHEN** OOS begins at a boundary date
- **THEN** the reported OOS series begins at that date (or first available on/after), even if warm-up uses earlier bars
