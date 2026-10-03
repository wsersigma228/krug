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

The name is Krug / Круг. The approved feed direction is a Pinterest-like responsive masonry grid with simple native sans-serif typography and proportional photographs. Simplicity and careful detail serve reading and writing; the interface remains a working application rather than a marketing page. Dark is the initial theme: cold graphite with a restrained saturated blue accent. Light and system themes remain available.

Post listings show the author, optional photo, optional title and text in that order. Titles can be omitted or cleared; post content remains required. Existing titled posts keep their titles. Untitled full posts expose an accessible heading without fabricating a visible title. The editor uses Create post, Save post and Title optional language.

Labelled navigation and language/theme preferences stay reachable in the sticky header. Scrolling down compacts it; scrolling up expands it with restrained motion and a reduced-motion alternative. The broad feed shell caps at 3600 CSS px and has no contextual author rail. Masonry cards adapt to their contents; mobile keeps one column and bottom navigation. Pages load 24 items at a time and offer Load more rather than automatic fetching while scrolling. Likes are available in listing cards; labelled comments links open discussion inside the full post. Loaded photos open an accessible native modal viewer; close button, Escape and backdrop click dismiss it and restore focus. The viewer reuses the loaded photo, preserves its proportions and releases page scroll lock on dismissal. Video support remains deferred. On wide desktop screens navigation is centered between the brand and account controls; search uses the available feed width. Tablet avatar and compose icons retain accessible names while reducing header crowding.

## Evidence on Hand

README.md, docs/api.md, docs/development.md and the current frontend/backend code.
The implementation is tested against real PostgreSQL and captured SMTP on Fedora.
Public production hosting and external SMTP are separate work.
