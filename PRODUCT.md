# Krug

<!-- impeccable:product-schema 1 -->

## Platform

Web first, responsive desktop and mobile browsers. Native HTML/CSS/JavaScript,
no frontend build or third-party browser runtime.

## Product Purpose

Help developers discover projects and people with a shared interest in building.
External projects bootstrap useful discovery while native projects and public
updates let people share their own work. Krug adds saved projects, project follows
and voluntary interest beyond an outbound source link.

## Users

Developers across disciplines, including open-source and game development, using
English or Russian. Search, project pages, updates and source links are available
without registration. An account is required to create, save, follow or mark interest.

## Capabilities and Constraints

The first version centers on native and externally imported projects. It includes
structured discovery, project drafts/publication, owner updates using existing
posts, save/follow/interested, saved and followed lists, and profiles visible in a
project's interested list only after explicit consent for that project. Interest
defaults private. Following stores a selection; project alert emails are deferred.
Import activity must not invent recruitment status, team size or commitment.

Public project and update URLs carry escaped HTML and object-specific OpenGraph
metadata. The interactive app supplies account actions; public share pages remain
useful without JavaScript or authentication. Existing accounts, author follows,
post publication, photos, stories, comments, reactions and email flows remain.

No teams/applications, chat, task management, billing, AI matching, reputation scores,
mobile app or federation in this version. FastAPI and PostgreSQL remain the backend;
the existing Redis/Celery mail pipeline stays. Fedora remains the deployment host.
User content is never translated. RU/EN account language and per-browser
light/dark/system themes remain available.

## Brand Commitments

Cold graphite and restrained blue, clear native sans-serif typography. Discovery
is an operating surface: prominent search, a desktop filter sidebar and compact
project cards; mobile filters collapse beneath search. Real titles, summaries,
skills, status and source take precedence over decorative imagery or fake metrics.
Stories retain their proportional-photo masonry layout outside primary discovery.

Motion communicates navigation and feedback: short ease-out opacity/transform
transitions, stable focused controls and reduced-motion support. No cinematic
scroll scenes, motion dependencies or mandatory animations.

## Evidence on Hand

Current backend/frontend code, Alembic migrations, tests, README and API guidance.
Verification results belong in the task report; this brief does not claim a live
deployment or complete runtime coverage by itself.
