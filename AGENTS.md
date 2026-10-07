# Development guidance

- Keep the native HTML/CSS/JavaScript frontend free of a build step.
- Prefer small changes using existing helpers and dependencies.
- Read current code and relevant documentation before editing.
- Never commit local environment files, credentials, database dumps or uploaded media.
- Preserve unrelated work and persistent data during updates.
- Keep README, API documentation and configuration examples consistent with changes.
- Run relevant Python and JavaScript checks. Integration tests require a separate test database.
- Follow docs/development.md for startup, migrations and verification on a Linux execution host.
- For continuation in a new chat, read docs/handoff.md and the relevant current-state Obsidian note first; verify Git/runtime facts before relying on historical check results. Do not repeat a whole-repository audit unless requested or required by a specific unresolved problem.
- Divide file ownership before delegation. Use a Luna role without a full-history fork for code and tests; keep root responsible for decisions and verification. One agent owns each browser session; reuse existing browser scripts and wait for actual data readiness. Keep required responsive, security and Fedora checks.
