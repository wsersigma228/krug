# Krug

<!-- impeccable:product-schema 1 -->

## Platform

Web first, responsive desktop and mobile browsers. Native HTML/CSS/JavaScript,
no frontend build or third-party browser runtime.

## Product Purpose

Help people find collaborators and organize work around shared interests. Public
discovery includes people who opt in, native and attributed external projects,
teams, events, communities, open roles and public updates. Collaboration is native
to Krug; imported source material remains clearly attributed and never implies
that an external maintainer is recruiting.

## Users

Developers across disciplines, including open-source and game development, using
English or Russian. Search, public listings, profiles and source links are
available without registration. An account is required to publish an intent
profile, create projects, teams, events or communities, apply to roles, manage
roles or publish community posts.

## Capabilities and Constraints

Discovery offers All, Projects, Teams, Events, Communities and People results.
The mixed All view combines bounded previews from actual sources; type tabs lead
to complete result lists. People choose whether their collaboration profile is
discoverable and may pause it at any time.
Profiles can include skills, interests, wanted skills, intent, timezone,
commitment, languages and external links. Private contact details are never
inferred from account email.

Members can start native projects independently of external repositories. Owners
publish real openings, receive applications and accept or reject them. Applicants
may withdraw. Contact URLs are shared only with the project owner and, after
acceptance, the accepted applicant. Owners and accepted members can publish
project updates using the existing post editor. Team owners manage openings and
applications, members and linked projects; teams can be associated with events.
Community owners manage their listing, and members can join, publish posts and see
other member posts; owners retain post moderation. Event owners manage event
details, participation and source links; users save events and independently mark
interest. Saved pages combine real saved projects, teams, events and communities.
Counts describe actual membership, interest, open roles and published updates; no
audience or recruiting figures are fabricated.

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
light and dark themes. Discovery places compact copy and prominent search above
the six result tabs, with a desktop filter rail and upcoming-events rail around a
mixed grid of real cards. Owner-provided covers and profile photos use real stored
media; missing images use type-aware fallback surfaces or initials. Mobile keeps
four real destinations reachable, collapses filters below search and brings an
actual card into the first viewport. Layouts stay fluid from narrow phones to
ultrawide screens; stories retain their proportional-photo masonry grid.

Theme changes use a native circular reveal where supported, preserving the same
controls and scroll position; interruption, fallback and reduced-motion paths
remain immediate. Existing navigation and feedback motion stays short, with
no cinematic scroll scenes, motion dependencies or mandatory animations.

## Evidence on Hand

Current backend/frontend code, Alembic migrations, tests, README and API guidance.
Verification results belong in the task report; this brief does not claim a live
deployment or complete runtime coverage by itself.
