# Project discovery (v0.1)

Krug connects developers with native projects and public GitHub projects.
Anonymous visitors can search, filter, read project pages and published updates,
and open external sources. Accounts are required only to create/edit projects,
publish updates, save, follow or express interest.

## Deliberate boundary

Native projects and imported repositories share `Project`. A nullable
`posts.project_id` gives a post the product role of project update without moving
post IDs, photos, likes or comments. Existing standalone stories and author follows
remain supported. Project owners alone edit their projects and publish updates.
Account removal is refused while the user owns a project; deleting an account
must not silently erase project history. Ownership transfer is not implemented.

Teams, applications, game-jam/hackathon collectors, chat, saved-search alerts,
matching and billing are outside v0.1. An imported repository is not a promise
that its maintainers are recruiting. Repository contributors are not team size.
The API deliberately returns unknown recruitment/stage when not established.

Save is a private bookmark. Follow persists an in-app following list, without
automatic email alerts. Interested is independent of both and is private by
default. The per-project visibility control opts the user into the interested
people list; private interest is never exposed through that list.

## GitHub automation

`python -m backend.github_import [owner/repository ...]` imports bounded public
repository metadata. `GITHUB_REPOSITORIES` configures a comma-separated shortlist
(maximum 20); without it the collector uses eight repositories covering game,
web and tool development. No full README, private repository, contributor profile
or arbitrary submission URL is fetched. `GITHUB_TOKEN` is optional and must stay
in private environment configuration, never frontend code.

Existing Celery beat schedules refresh every six hours. A PostgreSQL transaction
advisory lock prevents overlapping collectors. Failed imports do not remove
existing records. HTTP 403/429 stops the batch rather than burning the API budget.
Requests have a 15-second timeout, a 512-KiB response cap, and redirects restricted
to GitHub's repository API. Logs contain error types, not payloads or credentials.

Unique source/external IDs make reimport idempotent; canonical repository URLs
provide additional deduplication. Repository rename preserves the Krug slug and
ID. A native project already using the canonical repository URL is preserved.
This is identity-based deduplication, not title/ML matching.

`last_activity_at` comes from the repository's pushed timestamp;
`last_verified_at` records a successful metadata check. They do not confirm that
an opening exists. GitHub archived/disabled repositories become archived.
Repositories without a push date or with activity older than 180 days are stale;
previously active records not verified for seven days also become stale. These
initial thresholds concern repository activity, not all future opportunity types.
Stale/archived records remain accessible but are excluded from default discovery;
explicit status filters can show them. Exact `game dev` aliases match
`gamedev`/`game-development` tags or skills; there is no semantic/ML search.

Sources: [GitHub repository API](https://docs.github.com/en/rest/repos/repos#get-a-repository),
[API best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).

## Public sharing

`/project/{slug}` and `/project/{slug}/updates/{id}` return public server-rendered
HTML with object-specific title, description, canonical and OpenGraph metadata.
Set `PUBLIC_APP_URL` to the externally reachable HTTPS origin for useful share
previews. A loopback URL is suitable for local preview only. Draft projects and
updates return no public content. The native application provides editing and
interactive discovery; it still has no frontend build step.

## Explicit fresh start

`python -m scripts.bootstrap_krug --expected-database NAME --reset-data` is an
operator command, never a migration or automatic startup action. It reads the
developer account/password JSON from stdin, requires the explicitly named
application database, clears known application tables in one transaction while
preserving Alembic/schema, and creates the configured developer account and Krug
project. It does not write progress updates or grant an administrative role.

Before using it, stop application writers, create a private PostgreSQL custom-format
dump and media archive, verify both, and preserve `.env` and volumes. The command
does not delete media files; remove old task-specific media only after checking
the backup and ownership. Never put the stdin payload in Git or command arguments.

## Verification

Run the full PostgreSQL suite on an exclusive `test_db`, including projects,
privacy, pagination and GitHub normalization/upsert checks. Collector tests use
synthetic payloads; a successful live import is a separate operational check.
Check desktop/mobile, keyboard, reduced motion, RU/EN, light/dark, empty results,
authentication return and failed network requests with the browser scripts.

Search is PostgreSQL-based. A large GitHub project's presence proves catalog
supply, not teammate availability or successful collaboration. Validate actual
discovery utility with people using real queries before widening import scope.
