# Discovery and collaboration

Krug connects people through native and external projects, independent teams, events, communities and opted-in collaboration profiles. GitHub and GitLab supply bounded public project metadata.
Anonymous visitors can search, filter, read project pages and published updates,
and open external sources. Accounts are required to create/edit projects, apply
for roles, publish updates, save, follow or express interest.

## Deliberate boundary

Native projects and imported repositories share `Project`. A nullable
`posts.project_id` gives a post the product role of project update without moving
post IDs, photos, likes or comments. Existing standalone stories and author follows
remain supported. Project owners alone edit project metadata; owners and accepted
members can publish updates. Only an update's author can edit or delete it.
Account removal is refused while the user owns a project, team, community or event; deleting an account
must not silently erase project history. Ownership transfer is not implemented.

Applications and membership now connect people to roles on owned projects. An
imported repository is still not a promise that its maintainers are recruiting;
unowned external records cannot open roles or accept applications. Repository
contributors are not team size. Stage and recruitment stay unknown unless a
reviewed owner establishes them. Chat, event collectors, saved-search alerts,
automated matching and billing remain outside this scope.

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

External metadata submitted by users stays private until an admin approves it;
approval creates an unowned external project and never asserts maintainer access.
An imported project claim requires evidence and admin approval before assigning
an owner. Claimed projects retain external source fields and IDs, and the GitHub
collector skips their later updates. A native project inspired by an external
record stores `derived_from_project_id` and does not reuse its canonical URL.

Sources: [GitHub repository API](https://docs.github.com/en/rest/repos/repos#get-a-repository),
[API best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).

## Public sharing

`/project/{slug}` and `/project/{slug}/updates/{id}` return public server-rendered
HTML with object-specific title, description, canonical and OpenGraph metadata.
Set `PUBLIC_APP_URL` to the externally reachable HTTPS origin for useful share
previews. A loopback URL is suitable for local preview only. Draft projects and
updates return no public content. Project pages include factual consented interest,
membership, open-role and published-update counts, current role listings and public
member names, with no private contact links. The native application provides
editing and interactive discovery; it still has no frontend build step.

`/profile/{username}` shares public identity and project history. Current intent
appears only while collaboration discovery is opted in, active, and updated in
the last 30 days. `/people` applies the same visibility rule; account email and
private application/contact-settings URLs are never public. Profile external links
are public when their owner opts into discovery. Public project responses report consented interest, actual
members including the owner, open roles, and published updates. Private interest,
saves and follows do not create public counts. Accepting an application creates
one membership. The owner and accepted applicant receive each other's supplied
contact links only after acceptance. A member sees their own drafts; other members
see published updates only.

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

## Independent teams, events and communities

Teams can recruit before a project exists. Owners publish openings, review
applications and accept members; creating a native project transfers current
membership atomically while keeping the team record linked. Events describe a
hackathon, game jam, meetup or other opportunity and can have multiple participant
teams. Communities already include join/leave membership, member publications and
owner moderation. Stories remain independent. Saves remain private; visible
interest requires explicit consent on each team/event/project.

Native creation and manually attributed external events accept any supported safe
HTTP(S) source URL. The source list is open. GitHub and GitLab are the current
project collectors; neither metadata nor popularity implies recruitment. GitLab
uses its documented [Projects API](https://docs.gitlab.com/api/projects/) for an
explicit `GITLAB_PROJECTS` list of up to ten public namespace/project paths, with
subgroups allowed. The default list is empty; configure it to enable real supply.
The existing worker refreshes it every six hours, preserves claimed/native
records, bounds response sizes and handles API failures. No credentials are needed
for public GitLab.com projects. Events from other sources can be attributed
manually; automatic jam/event collection is not implemented.

Covers and public profile photos are uploaded by their owners. Missing covers
have neutral fallbacks; production never receives artificial members or fixture
activity. Preview fixtures and generated illustration art are disposable test
content, separate from the deployment database and repository assets.

People support language filtering as well as skills/interests search. Participation
format applies to projects, teams, events and communities; it is not inferred
for people. Project formats include unspecified, online, local and hybrid.
