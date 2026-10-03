# Круг

<!-- impeccable:product-schema 1 -->

## Platform

web — responsive desktop and mobile browser UI.

## Product Purpose

A small social blog for publishing text and an optional photo, following authors,
reading their stories and discussing them. The project is WIP.

## Users

Readers and authors using Russian or English. A narrower audience is undecided.

## Capabilities and Constraints

Native HTML/CSS/JavaScript with no frontend build or external runtime. FastAPI,
PostgreSQL, Redis and Celery run on Fedora. Preserve the existing account,
draft/publication, profile, follow, search, like, comment and notification flows.
Translate interface and service emails, never user content. Account language
syncs across devices; theme stays in each browser. Anonymous defaults follow
browser language and a cold graphite dark theme, with persistent manual overrides.

## Brand Commitments

The name is Круг / Krug. The approved direction combines a compact social feed
with the quieter pace of an author journal, simple sans-serif typography and care
for photographs. Simplicity and careful detail serve reading and writing;
the interface remains a working application rather than a marketing page.
The user rejected generic monochrome cards, pastel accents and narrow desktop
feeds. Dark is the initial theme: cold graphite with a restrained saturated blue
accent. Light and system themes remain available. Native sans-serif headings,
controls and reading text use the same system font.

Labelled navigation and language/theme preferences stay reachable in the sticky
header. Scrolling down compacts it; scrolling up expands it with restrained motion
and a reduced-motion alternative. Wide feeds use a centered shell capped at
1600 CSS px, with a contextual rail of authors from loaded stories and photos below text at every
width. Likes are available in listing cards; labelled comments links open discussion
inside the full post. Text-only posts, forms and articles retain readable line lengths.
Photos keep their proportions; mobile keeps one column and bottom navigation.
At tablet widths, avatar and compose icons retain accessible names while reducing
header crowding. The reading hierarchy distinguishes authors, story titles and
dates without enclosing each story in a card.

## Evidence on Hand

README.md, docs/api.md, docs/development.md and the current frontend/backend code.
The implementation is tested against real PostgreSQL and captured SMTP on Fedora.
Public production hosting and external SMTP are separate work.
