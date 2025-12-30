## ADDED Requirements

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

