# Development guidance

- Keep the native HTML/CSS/JavaScript frontend free of a build step.
- Prefer small changes using existing helpers and dependencies.
- Read current code and relevant documentation before editing.
- Never commit local environment files, credentials, database dumps or uploaded media.
- Preserve unrelated work and persistent data during updates.
- Keep README, API documentation and configuration examples consistent with changes.
- Run relevant Python and JavaScript checks. Integration tests require a separate test database.
- Follow docs/development.md for startup, migrations and verification on a Linux execution host.