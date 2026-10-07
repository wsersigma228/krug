# Collaboration UX audit

Baseline: `ab2677a`, 6 October 2026. Inspected current source and the Fedora
instance in Edge using Playwright, including discovery, the public Krug project
page and the developer profile. Screenshots and computed-layout evidence are in
the task's temporary artifact directory, outside Git. This audit explains the
correction; it does not claim the proposed changes have already passed checks.

## Findings and decisions

| Before | After | Why |
| --- | --- | --- |
| Project-only discovery; GitHub provenance leads every imported card | Search distinguishes projects, people and open roles; provenance is secondary to collaboration context | External supply provides context; useful actions must remain inside Krug |
| Native Krug appears after eight imports; cards expose no people, roles or updates | Native activity and real recruiting opportunities have a visible place; cards show factual activity and collaboration actions | Native value must be discoverable without inventing audience metrics |
| Interested ends at a saved checkbox state | Save, Follow and Interested retain separate choices; visibility consent is explicit, with links to interested people and roles | Expressing interest should connect to a useful workflow while preserving privacy |
| Imported projects have no owner or team workflow | Users can form a separate native project around an external source; claims require reviewed evidence | Interest in a repository is not permission to represent its maintainers |
| Profile leads with posts/followers/following and two top-level headings | Intent, skills, availability and factual project work lead; stories are secondary | Current willingness to collaborate is more useful than social popularity |
| Project details stop at description and engagement; no openings, applications or members | Description, people, roles, activity and updates have distinct sections | Search must lead to joining and building, not end at an outbound URL |
| Public project page contains only description, source, and an empty update list | Public pages expose the project's real collaboration context and useful next actions | Shared links should introduce the actual product |
| Discovery remains 1480px / three columns at 2560px and 3840px | Wider bounded discovery shell with increasing grid density; readable prose stays constrained | Use available space without stretching reading lines |
| Mobile filters retain their desktop-open state after resizing; header uses multiple rows | Compact mobile navigation and progressive disclosure of filters | Mobile is a separate usage context, not a shrunken sidebar |
| Same card entrance repeats across the result list | Restrained navigation, loading and state feedback with reduced-motion alternatives | Motion should explain changes and action completion |

At baseline, discovery's document width matched its viewport at 320px and 390px;
checked visible buttons/navigation controls met a 44px target. Retain these
properties. The public project page's maximum width was 880px at both desktop
and 4K; that reading measure is useful for updates but insufficient as the whole
project workspace. Existing palette, theme tokens, native controls, escaping,
auth return flow, pagination, reduced-motion and post/media functionality are
reusable.

## Product and privacy constraints

- Show real counts only. Private interest and saves must not appear as public
  activity. Public interested people require explicit per-project consent.
- People discovery requires explicit profile visibility consent and current
  active intent. No numeric reputation or inferred contributor availability.
- Owner controls openings and application decisions. Contact URLs are private
  until acceptance. A source repository is not a native Krug team.
- Do not add nonfunctional event/community tabs. Additional source/entity types
  can follow when their complete discovery flow exists.
- Preserve external provenance on claimed projects. Manual submissions and
  claims need review; never silently self-assign repository ownership.
- No fake developer updates, participant fixtures or popularity metrics in the
  working database.

## Acceptance checks

Viewport matrix: 320, 360, 390, 430, 768, 1024, 1280, 1440 and 1920px;
2560×1440, 3440×1440 and 3840×2160. Check horizontal overflow, visible touch
targets, grids, readable text, header/footer clearance and wrapped real content.
Inspect discovery, project, update, profile, create/edit and openings/applications
on mobile, 1440px and 4K. Exercise guest search, intent visibility, private
interest, public consent, application acceptance/rejection/withdrawal, contact
privacy, source-derived project creation, drafts, keyboard focus, RU/EN, themes,
loading/errors and reduced motion. Runtime results belong in the release report
and current project note, not in this baseline audit.

## Verification tools and limits

The reproducible preview checks are `scripts/browser_discovery_viewports.cjs`
and `scripts/browser_collaboration.cjs`. They refuse the working instance and
keep synthetic accounts/content in the disposable preview database. Screenshot
inspection covers populated discovery, projects, public updates, profiles and
forms at mobile, desktop, 2560×1440 and 4K sizes; viewport emulation is not a
physical-device test. Header size transitions were removed after the Impeccable
scan identified layout animation; state feedback uses opacity/transform.

The local `.impeccable/design.json` predates this correction. Its type/color
advisories are not a replacement for the current DESIGN.md or visual inspection.
The scan's missing-photo-src warning concerns the existing authenticated image
hydration path, which sets the image source after loading its authorized blob.
