## Why

The current management command name `research_eval` is unintuitive for end users. Renaming it to `backtesting` improves discoverability and aligns with typical workflow terminology.

## What Changes

- Rename Django management command from `research_eval` to `backtesting` (aggressive rename; no compatibility alias).
- Update all references in code, docs, and OpenSpec materials accordingly.

## Impact

- **Breaking change**: `python manage.py research_eval ...` will stop working after this change.
- Users must switch to `python manage.py backtesting ...`.
- Output directory naming and documentation references will be updated to stay consistent.

## Rollout / Notes

- This is an intentional hard rename (no deprecation period).
- Update CI/docs examples as part of the change to minimize user confusion.

