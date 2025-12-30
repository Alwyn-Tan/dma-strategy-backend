## ADDED Requirements

### Requirement: Explicit module boundaries
The system SHALL separate responsibilities into distinct modules:
- Django project configuration (`config/`)
- HTTP API layer (`api/`)
- Database domain models (`domain/`)
- Offline management commands (`tooling/`)
- Pure Python data pipeline modules (`market_data/`)
- Pure Python strategy engine modules (`strategy_engine/`)

#### Scenario: API layer stays thin
- **GIVEN** an API request is handled by a DRF view
- **WHEN** request validation and routing completes
- **THEN** the view delegates IO and computation to `market_data` and/or `strategy_engine`

### Requirement: Stable public API routes
The system SHALL keep API endpoints mounted under `/api/` with the same paths:
- `/api/codes/`
- `/api/stock-data/`
- `/api/signals/`

#### Scenario: Existing frontend integrations keep working
- **GIVEN** the frontend calls `/api/stock-data/` with existing query parameters
- **WHEN** the backend is refactored to the new layout
- **THEN** the endpoint remains available and returns the same JSON structure as before

### Requirement: Tooling commands are isolated
Offline workflows (data preparation, research evaluation) SHALL be implemented as Django management commands under `tooling/management/commands/`.

#### Scenario: Batch download command is discoverable
- **GIVEN** a developer runs `python manage.py help`
- **WHEN** management commands are listed
- **THEN** offline commands appear under the `tooling` app and can be invoked without importing API modules

