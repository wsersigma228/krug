# Krug

<!-- impeccable:product-schema 1 -->

## Platform

Web first, responsive desktop and mobile browsers. Native HTML/CSS/JavaScript,
no frontend build or third-party browser runtime.

## Product Purpose

Help people find collaborators and projects around shared interests. Public
discovery includes people who opt in, native projects, externally sourced projects,
open roles and real project updates. Project activity and collaboration are native
to Krug; imported source material remains clearly attributed and never implies
that an external maintainer is recruiting.

## Users

Developers across disciplines, including open-source and game development, using
English or Russian. Search, project pages, profiles and source links are available
without registration. An account is required to publish an intent profile, create
projects, apply to roles, manage roles or post updates.

## Capabilities and Constraints

Discovery offers All, Projects, People and Open roles results. People choose
whether their collaboration profile is discoverable and may pause it at any time.
Profiles can include skills, interests, wanted skills, intent, timezone,
commitment, languages and external links. Private contact details are never
inferred from account email.

Members can start native projects independently of external repositories. Owners
publish real openings, receive applications and accept or reject them. Applicants
may withdraw. Contact URLs are shared only with the project owner and, after
acceptance, the accepted applicant. Owners and accepted members can publish
project updates using the existing post editor. Counts describe actual opted-in
interest, membership, open roles and published updates; no audience or recruiting
figures are fabricated.

External project suggestions and requests to represent an imported project enter
an administrator review queue. Approval retains source attribution. Public project
and update URLs carry escaped HTML and object-specific OpenGraph metadata. Existing
accounts, stories, photos, comments, reactions and email flows remain available.

No chat, task management, billing, AI matching, reputation scores, mobile app or
federation. FastAPI and PostgreSQL remain the backend; the existing Redis/Celery
mail pipeline stays. Fedora remains the deployment host. User content is never
translated. RU/EN account language and per-browser light/dark/system themes remain.

## Brand Commitments

Coral actions on graphite surfaces, with separate accessible coral/text pairs for
light and dark themes. Discovery places compact copy and a prominent search above
the result tabs, with a usable desktop filter rail and a balanced project grid.
Mobile keeps four real destinations reachable, collapses filters below search and
shows a project card early in the first viewport. Layouts stay fluid from narrow
phones to ultrawide screens; stories retain their proportional-photo masonry grid.

Theme changes use a native circular reveal where supported, preserving the same
controls and scroll position; interruption, fallback and reduced-motion paths
remain immediate. Existing navigation and feedback motion stays short, with
no cinematic scroll scenes, motion dependencies or mandatory animations.

## Evidence on Hand

Current backend/frontend code, Alembic migrations, tests, README and API guidance.
Verification results belong in the task report; this brief does not claim a live
deployment or complete runtime coverage by itself.
