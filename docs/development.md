# Development and deployment

`backend/` contains the FastAPI API, SQLAlchemy models and Celery tasks.
`frontend/` contains native HTML/CSS/JavaScript served under `/assets`; `/app` opens
the UI. Both run from the same web service. `alembic/` stores migrations, `tests/`
stores checks and `scripts/` stores launchers/smoke checks. Redis is Celery's broker;
the feed and search query PostgreSQL directly. Photos live outside the container.

## Environment

Use Python 3.14. Install runtime dependencies with
`python -m pip install -r requirements.txt -c constraints.txt`, or development
dependencies with `python -m pip install -r requirements-dev.txt -c constraints.txt`.
Constraints pin the versions; they are not a hashed lock file. No Node packages
are required. Node can check frontend JavaScript syntax without installing packages.

Create `.venv` with `python3.14 -m venv .venv` on the Linux execution host.
Run containers, databases, migrations and application services on that host.
An editing machine can check syntax without starting containers.

Copy `.env.example` to `.env`; set a generated `SECRET_KEY`, database credentials
and `PUBLIC_APP_URL`. Compose connects to its internal `db` and `redis` services;
host-side tools use `.env`'s `DATABASE_URL` and `REDIS_URL`. Never commit `.env`.
If you change ports, change the host URLs as well:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_PORT` | 8000 | Loopback web port |
| `DB_PORT` | 5432 | Loopback PostgreSQL port |
| `REDIS_PORT` | 6379 | Loopback Redis port |
| `MAILPIT_PORT` | 8025 | Loopback development mailbox UI |
| `DB_USER`, `DB_PASSWORD`, `DB_NAME` | See `.env.example` | Database initialization and application connection |
| `MEDIA_ROOT` | `media` | Host-side photo directory; Compose mounts its photo volume at `/app/media` |

Database initialization variables apply to a **fresh** PostgreSQL volume. An
existing volume keeps its database users and passwords. Update those deliberately
in PostgreSQL rather than deleting the volume to make configuration changes work.

## Start and update

On the execution host, use `./scripts/start --dev-mail` for captured mail or
`./scripts/start` for the SMTP configuration in `.env`. Keep the same mail mode
when updating. The launcher builds web, stops only web/worker/beat, starts
db/redis (and optional Mailpit) and waits for PostgreSQL TCP and Redis readiness,
runs `alembic upgrade head` using the new image, then
recreates the app services and waits for health. A migration error must be fixed
before starting services that need the new schema. Data volumes are preserved.

For manual development on Linux, start db/redis, migrate with
`.venv/bin/alembic upgrade head`, then run
`.venv/bin/uvicorn backend.main:api --reload`. Run Celery worker and beat separately
when testing mail (commands in README); use only one beat per deployment. Avoid
running the container and host web server on the same port.

Use your own checkout directory (for example `/srv/krug`) and SSH host alias.
The examples below use `app-host`; replace it with your configured host.
Before updates, inspect `git status --short` on both the editing machine and execution host. Commit
only task files, push the branch, and update the execution host to the same commit. Preserve
unrelated server changes and never use reset/clean to erase them. Deployment
verification includes `git rev-parse HEAD`, `alembic current`, container state,
app/worker logs and HTTP/smoke checks. Main should contain completed checked stages.

Ports bind to loopback. From Windows, forward them with:

```powershell
ssh -N -L 8000:127.0.0.1:8000 -L 8025:127.0.0.1:8025 app-host
```

Use adjusted ports for isolated clones. `COMPOSE_PROJECT_NAME` gives a separate
stack and separate named volumes; it is not enough by itself to prevent host-port
collisions. An isolated check needs a new checkout, project name, ports and `.env`.
Never point its tools or tests at the deployment database.

## Verification

Tests require a separate database named **`test_db`**, checked before connection.
On a fresh volume, `init-test-db.sql` creates it. For an existing volume create it
once with `./scripts/compose exec db createdb -U YOUR_DB_USER test_db`.
Set `TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:PORT/test_db`
if your credentials/ports differ from test defaults.

```bash
.venv/bin/python -m pytest -q
node --check frontend/app.js
node --check frontend/projects.js
node --check frontend/i18n.js
node scripts/check_i18n.cjs
.venv/bin/python -m scripts.smoke
.venv/bin/python -m scripts.smoke_accounts
```

Wait for web health before smoke checks. Smoke scripts default to loopback
8000 (and 8025 for Mailpit); set `APP_URL` and `MAILPIT_URL` for another stack.
Host-side `DATABASE_URL` and `REDIS_URL` must also refer to that stack. Account smoke needs Mailpit; all smoke
scripts create temporary accounts and remove them. `scripts.smoke_social` has a
prepare/check pair for testing photo persistence across web recreation (README).
Tests use rollback fixtures; concurrency checks deliberately commit UUID-named
entities and remove only those entities. Migration round-trip checks run only on
`test_db` and are unsuitable for a populated deployment database.

`GET /` checks that the process responds. `/health` checks PostgreSQL and Redis;
neither confirms SMTP delivery. Check worker/beat logs and use captured mail for
end-to-end development checks. CI runs the test suite and JavaScript syntax check;
browser layout and real container recreation still require separate verification.

Project discovery, the bounded GitHub collector, engagement privacy and the
explicit operator-only database reset are described in [discovery.md](discovery.md).
The regular launcher never resets application data.

Optional browser checks use Playwright installed in a separate tools directory:
set `NODE_PATH` to its `node_modules`, then run `node scripts/browser_smoke.cjs`.
Use `APP_URL`, optional `MAILPIT_URL` (to exercise captured confirmation/reset links),
and `BROWSER_CHANNEL=msedge` for an installed Edge rather than Playwright Chromium.
`BROWSER_OUTPUT` chooses the screenshot folder; otherwise a temporary folder is used.
The check covers 1440px desktop and 390px mobile viewports, temporary accounts,
photo drafts/publication, social interactions, search, errors and empty states.
It removes only its temporary accounts and captured messages.

`scripts/browser_discovery_viewports.cjs` checks 320px–3840px layouts, four mobile
destinations, collapsed mobile filters and RU/EN discovery labels, then captures
screenshots. It creates no fixtures and refuses any `APP_URL` except
`http://127.0.0.1:18103`; run it only against the isolated preview.

For collaboration UI checks, use only the isolated preview at
`http://127.0.0.1:18103`. Set `NODE_PATH` to the external Playwright install and
`BROWSER_CHANNEL=msedge`, then run `node scripts/browser_discovery_viewports.cjs`
for 320px–3840px viewport, keyboard, theme, reduced-motion and error-state checks.
`node scripts/browser_collaboration.cjs` creates synthetic preview accounts, projects,
roles and applications and captures populated screens; these fixtures remain in that
preview database. Set `BROWSER_ADMIN_USERNAME` to an admin already promoted in the
same preview database to include submission, ownership-review and claimed-project
edit checks. The script refuses any `APP_URL` other than the isolated preview.
For a focused pass over an existing pending item, use
`scripts/browser_admin_tail.cjs` with `BROWSER_EXTERNAL_TITLE` set to that item's
exact title; it approves the item, exercises a synthetic claim, then verifies edit
preserves the external source and existing status/stage. It uses the same preview-only
URL guard and synthetic admin setting.

`node scripts/browser_locale.cjs` checks the running application's RU/EN behavior,
account language persistence, untranslated user content and theme controls. It
uses the same external Playwright setup and `APP_URL`; run it against the Fedora
application after deployment. `scripts/check_i18n.cjs` checks the static copy
catalog without requiring the running stack.
`node scripts/check_header.cjs` verifies header direction changes, small scroll
jitter and the return to the page top without a browser.
`node scripts/check_likes.cjs` checks the shared like/unlike control, failures,
guest sign-in and detached screens without a browser.

## Interface preferences and localization

`frontend/i18n.js` contains the RU/EN static copy and browser preference handling;
`app.js` renders screens and saves signed-in language changes through
`PATCH /me/language`. User content is kept outside translation. Interface dates
follow the selected language; `search_language` remains an independent search mode.

On first visit, the first supported RU/EN browser preference is used;
otherwise English is used. Manual language choice is stored under `krug-language`.
Saved account language overrides the browser choice after sign-in. For an account
with null language, the UI saves its current choice on first authenticated load.
Service-link `?lang=ru|en` selects the language before opening the token form;
the token remains in the fragment. Account and publication mail reads the saved
recipient language at delivery time, falling back to English for unset accounts.

`krug-theme` stores `light`, `dark` or `system` per browser. System mode follows
`prefers-color-scheme`; theme does not sync through the account. Storage failures
allow preferences to work for the current visit. Without a saved choice, the UI
starts in the cold graphite dark theme with a warm coral accent. The native frontend
uses the system sans-serif font for headings, reading and controls. The sticky header
compacts on downward scrolling and expands upward; controls stay in the same DOM
and reduced-motion disables transitions. Story/feed pages use
`min(calc(100% - 64px), 3600px)`. Collaboration discovery uses an 1800px shell,
expanding to at most 2200px on wide viewports; project detail and updates cap at
1800px. Discovery presents native and external projects, opt-in people and actual
openings. Listings use a responsive CSS grid with 350px minimum columns, 8px
automatic rows and 24px gaps (16px on mobile). ResizeObserver measures intrinsic `.post-card-inner` height to update
outer card spans, including after image loads and reaction changes; it disconnects
before each screen render. Default grid row flow uses the response sequence;
keyboard and source order retain it, while varied card heights do not create uniform
visual rows. Mobile uses one column,
20px side padding and bottom-navigation clearance. Listing cards place proportional
photos before optional titles and text; full posts retain heading/photo/text order.
Photo buttons enable only after successful image loading; failures replace the
whole button with a hint. Clicking a loaded photo opens a native modal `dialog`
that reuses its blob URL. Close button, Escape and backdrop click dismiss it; native
modal behavior contains focus, and close cleanup restores the opener when connected
and removes page scroll lock. Viewer image errors close it and show feedback.
Screen rendering closes the viewer before revoking object URLs. There are no new
viewer dependencies or migrations; video remains deferred. At 1700px and wider,
the header uses three columns to center navigation between brand and grouped
controls. Tablet/mobile retain their prior row layouts. Search spans the feed
container rather than a separate 1000px cap.
Header
expanded/compact heights are 92/72px on desktop, 128/112px from 651–1399px,
and 100/88px on mobile. From 651–1000px, account/compose icons retain accessible
names and navigation labels use 12px type. Search labels remain accessible while
visually hidden. [DESIGN.md](../DESIGN.md) records the current shared visual system.
Likes in listing
cards load through the existing per-post API (up to 24 requests per page); failed
loads offer retry without showing an invented count. The shared like control
also serves the full post. Comments links open discussion inside the post via
`?comments=1`. RU/EN switches language; the theme icon opens labelled Light, Dark
and System buttons.
Apply migration `a75e9b024138`
before running code that reads `users.language`; existing rows remain null.
Optional post titles need no new migration: the existing non-null string column
accepts an empty string. Create defaults an omitted title to empty; update omission
preserves it and an empty string clears it. Explicit nulls are rejected, and content
remains required and nonempty. Publication emails fall back to 80 characters of
whitespace-normalized content when a title is empty. The native frontend requests
24 items per page and appends the next page only through Load more.

Run `tests/test_locale.py` alongside account/email/migration tests, and use the
browser smoke for language and theme controls on desktop/mobile. These commands
describe verification procedures, not a claim that a particular run passed.

## Backups and public hosting

Back up PostgreSQL and `post_media` together, plus your private `.env` separately.
Keep `SECRET_KEY` stable: rotating it revokes JWTs/cursors and makes queued account
link secrets unreadable. Ordinary container recreation preserves named volumes.
Do not run `down -v`, prune volumes or reset a database during an update.
Mailpit messages are temporary; its mailbox is not a backup.

For public hosting configure HTTPS, the actual public `PUBLIC_APP_URL`, trusted
proxy handling and your SMTP credentials. Compose alone does not provide a TLS
reverse proxy. Account rate limits use socket IP; unconfigured proxy forwarding
can make all visitors share an IP budget. SMTP authentication requires STARTTLS.
The WIP has no automatic backup/restore workflow; test your own restore procedure.

Коралловое оформление discovery: поиск над выдачей, отдельная форма фильтров с кнопкой применения, смешанная сетка реальных результатов во вкладке «Всё». Переключение темы использует native View Transition с круговым раскрытием 400ms от переключателя; при reduced-motion или недоступном API тема применяется сразу. Быстрые смены выбора отменяют прежнюю анимацию, сохраняя последний выбор.

`frontend/og-default.svg` — редактируемый источник общего OpenGraph изображения; `frontend/og-default.png` — экспорт 1200×630. PNG проверяется визуально после экспорта, SVG не заменяет PNG в OpenGraph.
### Platform preview

The additive platform migration is `db71e945ac30` after `c4e8d1a9b210`.
It adds independent teams, events, communities and media associations while
preserving existing projects, posts and accounts. Back up database and photo
storage before deployment; do not reset data to introduce these records.

`browser_platform.cjs` deliberately accepts only the isolated loopback preview
at port 18103. Set `BROWSER_ART_DIR` to an outside-repository folder containing
synthetic `project.png`, `team.png`, `event.png`, and `BROWSER_OUTPUT` for captures.
It creates disposable accounts/records and leaves them for visual inspection;
remove the verified isolated stack afterward. Never run it against production.
It exercises profile photos, event creation/attribution, team applications,
acceptance, team-to-project transfer, covers, community join/posts/moderation and
mixed saved content. Use the existing locale, collaboration and viewport scripts
for regression checks; compare screenshots with `docs/design/coral-concept.png`
separately. Functional success alone is not visual acceptance.

App CSS/JS URLs in index.html carry the coordinated release query 20261008-platform. Bump that value when shipping changed app assets: the HTML is no-store, while persistent browser caches can otherwise retain an earlier script after a deployment. This is a native cache key, not a frontend build step. Draft covers use authenticated blob requests in the app and join existing object-URL cleanup; never make draft media public to fix an image request.
