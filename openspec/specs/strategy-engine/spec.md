# strategy-engine Specification

## Purpose
TBD - created by archiving change add-advanced-dma-strategy. Update Purpose after archive.
## Requirements
### Requirement: Regime filter gates long exposure
In `advanced` mode, the system SHALL support a regime filter that disables long exposure unless `close > MA(regime_ma_window)` is true on the decision bar.

#### Scenario: Below regime MA disables long exposure
- **WHEN** the regime filter is enabled and `close <= MA(regime_ma_window)` on day `t`
- **THEN** the target exposure for execution on day `t+1` is `0`

### Requirement: Signal ensembling produces target exposure
In `advanced` mode, the system SHALL support ensembling across multiple MA pairs to produce a daily `target_exposure` in `[0, 1]`.

#### Scenario: All ensemble members agree long
- **WHEN** all configured MA pairs indicate long on day `t`
- **THEN** the target exposure for execution on day `t+1` is `1.0`

#### Scenario: Mixed ensemble produces partial exposure
- **WHEN** only a subset of MA pairs indicate long on day `t`
- **THEN** the target exposure for execution on day `t+1` is proportional to the fraction of long signals

### Requirement: Volatility targeting scales exposure inversely with volatility
In `advanced` mode, the system SHALL support volatility targeting that scales target exposure by inverse volatility, subject to caps.

#### Scenario: High volatility reduces exposure
- **WHEN** current volatility increases while `target_vol` is constant
- **THEN** the scaled exposure decreases, up to a minimum of `0`

#### Scenario: Leverage cap applies
- **WHEN** inverse-vol scaling would imply leverage above `max_leverage`
- **THEN** the scaled exposure is capped at `max_leverage * target_exposure`

### Requirement: No lookahead execution
The system SHALL avoid lookahead bias by using indicators computed on day `t` to determine actions executed no earlier than day `t+1` open.

#### Scenario: Decisions execute on next open
- **WHEN** the strategy updates target exposure based on day `t` close
- **THEN** the portfolio adjusts at day `t+1` open (or later), not intraday on day `t`

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

