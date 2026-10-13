---
name: Krug
description: Graphite, blue and orange collaboration discovery for people, projects, teams, events, communities and public updates. All screens follow the October 2026 redesign (docs/design/redesign-2026-10).
colors:
  canvas-light: "#f4f4f1"
  paper-light: "#ffffff"
  text-light: "#141414"
  muted-light: "#626262"
  line-light: "#e4e4df"
  soft-light: "#ededea"
  accent-light: "#1f6bff"
  on-accent-light: "#ffffff"
  hover-light: "#1858d9"
  accent-ink-light: "#0a4fd1"
  hero-light: "#17191c"
  hero-ink: "#f4f4f2"
  hero-muted-light: "#a3a5a8"
  hero-line-light: "#2c2f33"
  signal-light: "#ff6b2c"
  live-light: "#0f8a55"
  canvas-dark: "#0d0e10"
  paper-dark: "#16171a"
  text-dark: "#ececee"
  muted-dark: "#9a9ca3"
  line-dark: "#26282c"
  soft-dark: "#1e2023"
  accent-dark: "#5b95ff"
  on-accent-dark: "#06101f"
  hover-dark: "#7aa9ff"
  accent-ink-dark: "#8db5ff"
  hero-dark: "#131416"
  signal-dark: "#ff8a55"
  live-dark: "#4cc58b"
  entity-project: "#1f6bff"
  entity-team: "#12a26b"
  entity-event: "#ff6b2c"
  entity-community: "#8b5cf6"
  entity-person: "#e2a400"
  viewer-backdrop: "#080c12e6"
typography:
  headline:
    fontFamily: '"Krug Unbounded", "Krug Onest", ui-sans-serif, system-ui, sans-serif'
    fontSize: "clamp(1.5rem, calc(1.1rem + 1.2vw), 2.5rem)"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: '"Krug Geologica", "Krug Onest", ui-sans-serif, system-ui, sans-serif'
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  section:
    fontFamily: '"Krug Unbounded", "Krug Onest", ui-sans-serif, system-ui, sans-serif'
    fontSize: "17px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  body:
    fontFamily: '"Krug Onest", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.75
  excerpt:
    fontFamily: '"Krug Onest", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  share-headline:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(36px, 6vw, 52px)"
    fontWeight: 650
    lineHeight: 1.15
  discovery-headline:
    fontFamily: '"Krug Unbounded", "Krug Onest", ui-sans-serif, system-ui, sans-serif'
    fontSize: "clamp(19px, 1.6vw, 25px)"
    fontWeight: 650
    lineHeight: 1.1
  discovery-card-title:
    fontFamily: '"Krug Geologica", "Krug Onest", ui-sans-serif, system-ui, sans-serif'
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.25
  discovery-card-summary:
    fontFamily: '"Krug Onest", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.35
  label:
    fontFamily: '"Krug Onest", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 600
  metadata:
    fontFamily: '"Krug Onest", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "12px"
  author:
    fontFamily: '"Krug Onest", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 600
rounded:
  text-control: "4px"
  field: "0.45rem"
  control: "0.55rem"
  card: "0.55rem"
  badge: "999px"
  photo: "14px"
  circle: "50%"
spacing:
  compact: "8px"
  field: "12px"
  block: "16px"
  form: "18px"
  section: "20px"
  card: "24px"
  wide-media: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.on-accent-light}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-primary-dark:
    backgroundColor: "{colors.accent-dark}"
    textColor: "{colors.on-accent-dark}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.hover-light}"
  button-secondary:
    backgroundColor: "{colors.soft-light}"
    textColor: "{colors.text-light}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.text-light}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.text-light}"
    rounded: "{rounded.text-control}"
    padding: "8px 0"
  input:
    backgroundColor: "{colors.paper-light}"
    textColor: "{colors.text-light}"
    rounded: "{rounded.field}"
    padding: "12px"
  navigation:
    textColor: "{colors.muted-light}"
    padding: "10px"
  badge:
    backgroundColor: "{colors.soft-light}"
    textColor: "{colors.muted-light}"
    rounded: "{rounded.badge}"
    padding: "4px 8px"
  card:
    backgroundColor: "{colors.paper-light}"
    textColor: "{colors.text-light}"
    rounded: "{rounded.card}"
    padding: "24px"
  viewer-close:
    backgroundColor: "{colors.paper-light}"
    textColor: "{colors.text-light}"
    rounded: "{rounded.control}"
    padding: "10px"
    width: "44px"
    height: "44px"
  post-card:
    backgroundColor: "{colors.paper-light}"
    textColor: "{colors.text-light}"
    rounded: "{rounded.card}"
    padding: "20px"
---

# Design System: Krug

## Overview

**Creative North Star: "A practical place to find collaborators"**

Krug helps people find collaborators through projects, teams, events, communities and opt-in profiles. Blue actions distinguish active choices against a graphite header band and neutral surfaces; orange marks the active destination and today. Stories retain their responsive masonry grid, proportional photos, optional titles and readable text.

Dark is the initial theme; saved Light, Dark and System choices remain effective. Both themes share their geometry. The sticky header keeps the top-left wordmark, labelled navigation, language/theme preferences and account/write actions available on a graphite band that stays at a fixed height (the earlier compaction on scroll and its scroll listener are removed). Russian and English interface copy changes independently of user stories, names and biographies.

The visual foundation (tokens, fonts, header, dock, base components) follows the approved October 2026 redesign; all screens are migrated (steps 1–4: foundation, discovery home, detail pages, lists, forms, settings, applications, updates and admin). A standalone monochrome theme is dropped.

**Key Characteristics:**

- Graphite header band and neutral surfaces with accessible blue actions and orange signal.
- Self-hosted Unbounded (display), Geologica (card titles) and Onest (UI text), all with Cyrillic.
- Distinct cards for people, projects, teams, events and communities; factual counts only.
- Responsive masonry cards with proportional photographs for Stories.
- Persistent preferences and a sticky graphite header with search.

## Colors

The shared palette pairs blue accent and orange signal with cool neutral surfaces and a graphite hero band; the frontmatter records the light and dark values. Entity colours (project blue, team green, event orange, community violet, person amber) are exposed as `--c-*` tokens with per-type button pairs `--c-btn/--c-on/--c-ink` through `data-type` or `.type-*`; screens adopt them in later steps.

### Primary

- **Accent / On accent:** blue primary buttons, focus rings and selection. Light mode uses white labels; the brighter dark-mode blue uses dark labels to preserve contrast. Primary hover uses Hover; text links use Accent ink.
- **Hero and signal:** the header is graphite (`--hero`, with `--hero-ink/-muted/-line`) in both themes. Signal orange marks the active navigation underline and the current-day line; Live green marks running events.

### Neutral

- **Canvas:** page background.
- **Paper:** post cards, forms, settings/authentication cards, theme disclosure and mobile bottom navigation.
- **Text:** story copy, authors and primary headings.
- **Muted:** metadata, introductions, hints and inactive navigation.
- **Line:** one-pixel card borders, discussion dividers and secondary hover fill.
- **Soft:** secondary controls, selected likes, avatar discs, badges, photo backdrop and mobile active navigation.
- **Viewer backdrop:** a dark translucent overlay behind the modal photo in both themes.

The live CSS variables `--canvas`, `--paper`, `--text`, `--muted`, `--line`, `--soft`, `--accent`, `--on-accent` and `--hover` map to the corresponding light values at the root and dark values under `data-theme="dark"`. Frontmatter component variants use the light baseline unless explicitly labelled dark.

**The Blue Action Rule.** Use blue for actions, orange only for the active destination and today markers; let neutral surfaces frame user content and retain photographs in their original colors.

## Typography

**Interactive app fonts:** locally hosted variable fonts declared in `frontend/fonts/fonts.css` (licences beside the files, OFL). Unbounded is for the wordmark, page titles, section headings and big numbers; Geologica (weight 700, `SHRP` 60) for card and box titles; Onest for all UI and body text. The root size is fluid: `clamp(15px, calc(10.5px + .3vw), 20px)`. There is no third-party font request. Font synthesis is disabled. Static public share pages use the system sans-serif stack declared in `frontend/share.css`.

### Hierarchy

- **App headline:** regular route headings use `clamp(1.5rem, calc(1.1rem + 1.2vw), 2.5rem)` in Unbounded and become (26px) on narrow screens; headings wrap anywhere so long Russian words never overflow. Public share headlines use `clamp(36px, 6vw, 52px)`.
- **Story title and excerpt:** story links use (22px), increasing to (23px) on mobile; excerpts use (16px), preserve newlines and cap at (75ch). Full story copy uses (18px), reducing to (17px) on mobile, preserves newlines and stays within (70ch).
- **Discovery hierarchy:** the compact discovery heading uses `clamp(19px, 1.6vw, 25px)` on desktop, (18–23px) through tablet widths and (17–22px) on phones. Card titles use (17px) with (14px) summaries. These compact discovery sizes are separate from the story scale.
- **Section:** app section headings use (17px) Unbounded, (16px) on mobile. Public share section headings use (24px).
- **Label:** compact action controls; field labels use weight (550). General introductions use (16px), line-height (1.6) and maximum width (65ch), reducing to (15px) on mobile. Discovery introductions use (15px) desktop and (12px) on narrow screens.
- **Metadata:** dates use tabular numerals and sit below the author beside a two-row avatar; size is (12px). Author names retain (14px) and weight (600), separating identity from the quieter date. Hints use (13px) and line-height (1.55).
- **Metadata:** dates use tabular numerals and sit below the author beside a two-row avatar; size is (12px). Author names retain (14px) and weight (600), separating identity from the quieter date. Hints use (13px) and line-height (1.55).

The lowercase "krug" wordmark (a ring plus Unbounded text) uses (1.25rem) and tracking (-0.035em). It is an identity treatment, not the page heading.

**The Reading First Rule.** Keep stories readable without photographs, preserve user line breaks and allow long text to wrap.

## Layout

The desktop shell uses a centered width `min(calc(100% - 64px), 3600px)`. Discovery caps at (2060px) on ordinary desktop widths and up to (2200px) on ultrawide screens; project detail and updates remain capped at (1800px). Story/feed pages retain the broad shell. Page vertical padding is (44px) above and (96px) below.

Post listings use CSS Grid with `repeat(auto-fill, minmax(min(100%, 350px), 1fr))`, (8px) automatic rows, default row flow and (24px) gaps. Card heights follow their intrinsic contents, including photo loading, wrapping text and changing reaction controls. Native ResizeObserver measures each inner card and updates its outer grid span; the observer is disconnected before each screen render. Cards keep DOM and keyboard order from the paginated response. Default row flow places cards in that sequence, while differing card heights prevent a uniform visual row rhythm. The first request loads up to (24) items; Load more appends the next page. Scrolling alone does not fetch another page.

Listing photos appear after the author and before the optional title and text. Full posts retain heading, optional photo and full text order; an untitled full post has a visually hidden Post heading rather than an invented visible title. Text-only cards retain the same controls and reading path.

**Discovery home (redesign step 2).** The "All" tab without a search or filters is built by `frontend/home.js`; with a search or filters, or on any other tab, the result lists use the same band, tabs and cards (step 4). It uses real API data only and leaves a block out when its data is empty or failed. Under the header sits a graphite band (the Hero colour). Signed in: "Привет, {display name}", a summary line of real counts (accepted applications, events this week) and a "now and soon" strip of up to three events (active first and wider; chip live/registration/deadline within 72 hours/soon; countdown computed in the browser and refreshed each minute; a phase bar from the deadline, start and end that exist, with a visually hidden text equivalent). Guest: headline "Найди, с кем и что делать", large search, static skill shortcuts and the next event. Below: type tabs (no counts, the API has none), "Ищут людей" (project and team roles merged newest first, open-slot chips, "Откликнуться"; guests are sent through login), "Календарь событий" (28 day columns, a "сегодня" line; a list with per-row bars at 700px and below), "Проекты, сообщества и люди", and from 1500px a right rail "Ваши заявки" (latest three). Entity colours use `.type-*`; countdowns and numbers use the display font. Geometry from data is applied through CSSOM (`data-grow`, `data-col`, `data-at`, `data-k`) because the CSP forbids inline style attributes. Content is capped at 2400px; the layout is checked from 320px to 3840px.

**Detail pages (step 3).** Project, team, event, community, profile and post pages share `detailHead` / `detailSubnav` / `detailBind` (`frontend/platform.js`): a head tinted with the entity colour (`.dt[data-type]`), breadcrumbs, emblem or cover, a large faint monogram, meta line and actions with the primary action in the entity colour (`--c-btn`/`--c-on`); a sticky section sub-nav whose links scroll in place without changing the hash route; content in `.dt-box` panels (`.dt-box-h` heading with an entity-colour square, `.dt-box-b` body) with a right rail for calls to action and facts (`.dt-facts`). Standalone posts use the person colour, project updates the project colour, community posts the community colour.

**Lists, forms and account screens (step 4).** Lists, search results, roles, saved items, people, updates, settings, applications, the admin queue and "who is interested" open with the graphite page band (`listBand`) and continue in `.hm-wrap.lst`; cards follow the home card language (entity colour, first-letter cover fallback, Geologica titles, status chip). Search results name the query in a highlighted mark. Editors use a lighter entity-tinted head (`formHead`) and group fields in `.dt-box` sections, with cover and visibility in a rail from 1000px; submit buttons take the entity colour. Field borders keep at least 3:1 contrast (`--field-line`). Sign-in, registration and recovery use a compact card on the graphite background. Settings use a section nav on the left from 900px (a scrolling row below).

The header is one row, (3.9rem) high, inside a centred container of at most (2400px): wordmark, navigation, a search field (up to (30rem); light field on graphite, dark field in the dark theme), language/theme controls, account and a primary "Create" action (signed in). Search submits to the discovery query (`#explore?kind=all&search=…`). Below (1080px) the search field is hidden; below (1300px) the username is hidden; below (560px) "Create" shrinks to an icon.

The header keeps controls and focused elements in the same DOM. At widths up to (850px) the five primary destinations (Discover, Teams, Events, Communities, You) move to the fixed bottom navigation, whose current item carries an orange mark; reduced motion disables transitions.

At (650px) and below, the header stays one row and the fixed bottom navigation carries the five primary destinations. General content uses the full width, (20px) side padding and bottom clearance `calc(100px + env(safe-area-inset-bottom))`; discovery overrides its top and side spacing to stay compact. Story search moves the language select to a second full-width row; ordinary fields use (16px) text while this select uses (13px). Search labels remain accessible while visually hidden. Toasts clear the bottom navigation and safe area. 

At mobile widths, project, person and role cards become one column with (16px) gaps; the Stories masonry grid also becomes one column. Authentication forms cap at (490px). Tabs, statistics and action controls wrap.

## Elevation & Depth

Post cards and form/settings/authentication containers use Paper and one-pixel Line borders. Cards remain flat at rest; their different heights come from content rather than fixed image crops. The header and bottom navigation remain solid. The only box shadows belong to transient surfaces (toast, theme menu): `0 8px 28px #14141424` in light mode and `0 8px 28px #00000066` in dark mode.

**The Flat Surface Rule.** Separate resting content with cool surfaces and dividers; reserve the shipped shadow for transient toast feedback.

## Shapes

Fields use the field radius (0.45rem); controls, tabs, cards and containers use the shared radius (0.55rem) at every width. Badges and tags are pills. Photos use the photo radius; toasts and editor previews use the feedback radius. Status badges have the badge radius. Avatars are circular (32px), with a profile variant (72px). The top-left brand mark is a circular outline in the header ink colour (1.4rem). Interface SVG icons use (20px) dimensions, with a filled heart for liked state.

## Components

### Buttons

Primary actions use Accent/On accent, minimum height (44px) and compact padding. Secondary/liked controls use Soft/Text. Destructive actions are transparent with a Muted border and fill with Signal on fine-pointer hover. Text actions remain transparent and underline on hover. Disabled buttons show wait cursor and opacity (0.55); pressed controls scale to (0.98).

Transform/background transitions use (150ms ease-out). Fine-pointer hover avoids sticky touch states. Keyboard focus uses a (2px) Accent outline with (2px) offset for controls and links (white inside the graphite header); fields show an Accent border with a soft ring.

### Cards / Containers

Post cards carry a (32px) circular avatar spanning two metadata rows, an author name, date, optional photo, optional title, linked excerpt and wrapping interaction toolbar. Inner padding is (20px), reduced to (18px) on mobile. Excerpts show up to (260) characters with an ellipsis and Read more when needed. Titles are omitted when empty; text links to the full post and the photo opens its viewer. Form/settings cards use Paper, Line borders and padding (24px; 18px mobile). Authentication card padding is (28px desktop; 20px mobile). Empty states use a solid Line border, Paper background and card-radius corners with centered copy and an action when available.

### Inputs / Fields

Native inputs, selects and resizable textareas use Paper/Text, a Line border and minimum height (44px). Placeholders use Muted at full opacity. Focus shifts the border to Accent while retaining the keyboard outline. Textareas have minimum height (110px), or (310px) in the story editor. Native checkboxes use Accent and (18px) dimensions; their labelled row remains at least (44px) tall.

Search uses a quiet Paper field with an initially transparent border and an Accent focus border. Its visible hierarchy comes from the query, language select and submit action; labels and explanatory text remain available to assistive technology without adding a second visible label row.

### Navigation and tabs

Desktop navigation combines inline SVG icons and labels at (14px), weight (550), minimum height (46px) and padding (10px). Header navigation sits on graphite with Hero muted labels; the active destination turns white with a Signal bottom border and `aria-current="page"`. In other navigation patterns active destinations use Text; inactive fine-pointer hover uses Soft/Text. Mobile stacks icons above (10px) labels on a Paper dock; the current item uses Text and a Signal mark above it. Current destinations expose `aria-current="page"`. Discovery tabs use (13px) type and a Text underline; shared feed tabs fill the active tab with Text/Paper.

### Badges and feedback

Draft/status badges are non-interactive Soft/Muted annotations at (11px). Errors and success messages use explicit text on Soft; errors also have a Muted border. Loading uses readable status copy with a (16px), one-second linear spinner. Toasts use the graphite hero colours with a hero line border, the transient shadow and (180ms ease-out) opacity. Feedback is announced through `role="status"` and `aria-live="polite"`.

### Photographs

Photos use automatic width and height, maximum width (100%), `object-fit: contain`, and top/start alignment. They retain intrinsic proportions rather than filling a prescribed frame or grid-row height. Feed maximum height is (560px desktop; 450px mobile); article maximum is (680px desktop), with the mobile feed limit overriding it. Editor previews cap at (280px). Optional photos do not determine whether text-only stories remain useful.

Loaded post photographs use a native button with a zoom-in cursor and no fill, scaling or padding. The button stays disabled until the image load event succeeds; an unavailable image replaces the entire button with readable status text. This pattern is shared by listing cards, full posts and existing editor photos.

### Photo viewer

A native modal dialog displays the already loaded photograph without another photo fetch. Its transparent, borderless frame caps at (96vw / 96dvh); the image preserves its proportions within (92vw / 84dvh), uses `object-fit: contain` and field-radius corners. The dark translucent backdrop isolates the photo. A fixed Paper/Text close button is (44px) square, positioned at least (16px) from the top and right while respecting safe-area insets.

Close button, Escape and backdrop click dismiss the viewer. Native modal behavior contains keyboard focus; dismissal restores focus to the opening photo button when it remains connected and releases page scroll lock. Screen rendering closes the dialog before revoking its photo object URL. Viewer image failure closes the dialog and announces unavailable-photo feedback. Video playback remains deferred.

### Preferences and motion

A RU/EN button shows the current language and names the target language for assistive technology. The theme icon opens a native details disclosure with labelled Light, Dark and System buttons, pressed state, Escape handling and focus return. Both controls remain reachable in every header state. Theme changes apply without replacing the screen; language changes preserve active form content and selected photos. Reduced-motion preference disables transitions and animations, including header motion, while retaining readable loading status.

### Post interactions

Listing cards place Like and labelled Comments together below the photo and text, before reading/edit actions. The compact like control shows its icon and count while retaining its state and action in an accessible name. Likes use the existing API and show confirmed count/state; unavailable counts offer retry. The full post uses the same like control. Discussion lives inside the article below its action toolbar; comment metadata stays grouped and only delete moves to the far edge. Comments links scroll to discussion with clearance for the sticky header.

## Do's and Don'ts

### Do:

- **Do** use shared theme variables and the recorded graphite/blue/orange palette.
- **Do** follow the font roles: Unbounded for titles, Geologica for card titles, Onest for the rest.
- **Do** preserve proportional photographs and readable text-only posts at every width.
- **Do** allow an empty title without introducing a synthetic visible heading.
- **Do** keep labelled navigation, account/write actions and preference controls reachable at every width.
- **Do** retain visible keyboard focus, wrapping text and reduced-motion behavior.
- **Do** clear mobile bottom navigation with safe-area padding.

### Don't:

- **Don't** replace the graphite, blue and orange palette with pastel accents.
- **Don't** stretch photographs to grid height, force square crops or make stories depend on an image.
- **Don't** translate user stories, names or biographies with interface copy.
- **Don't** extend the toast shadow into resting post cards or add cinematic motion.

Documentation is derived from the current frontend source. Temporary synthetic review content is verification evidence, not shipping imagery or product copy.


## Project discovery and sharing

Collaboration discovery uses graphite, blue and orange, with light and dark accent/text
pairs. Its tabs are All, Projects, Teams, Events, Communities and People. All
interleaves real records from native and external projects, teams, events,
communities and opt-in people in a shared card grid. Empty sources do not leave
blank sections; source failures keep their own error messages. Compact copy and
prominent search sit above the tabs. Desktop places filters in a left rail and
upcoming real events at right; the center grid stays balanced. Intermediate
viewports collapse the right rail before the filters. Mobile keeps search and tabs
near the top, collapses filters by default and uses four real destinations in the
bottom navigation. The discovery shell grows fluidly from narrow phones through
ultrawide displays.

Projects, teams, communities and events may have owner-uploaded cover images.
Cards without a cover use a type-specific neutral fallback; profile cards use a
real uploaded avatar or initials. Generated preview art is not shipped as user
content.

Native project counts reflect real opt-in interest, membership, open openings and
published updates. An external source card explains that its source does not
indicate recruitment. People control profile discoverability and can pause it;
private account email is not exposed as contact information. Project detail pages
pair the description with the next relevant action, actual members, openings and
updates. Owners manage roles and applications; applicants can withdraw. Contact
URLs are shown only to owners and accepted applicants. Owners and accepted members
can post project updates using the existing editor. External submissions and
ownership claims enter administrator review and keep their original attribution.
Public share pages remain useful without authentication; drafts stay private.

Theme changes use a (400ms) circular reveal from the theme control through the
native View Transition API when supported and motion is allowed. It updates the
same document without replacing controls or resetting scroll. New changes skip an
in-flight transition, unsupported browsers apply the theme immediately, and
reduced motion bypasses the transition. Result changes use short opacity/transform
transitions; there is no motion library or scroll choreography.

Public story and update pages use share.css with readable 880px measure, native typography,
proportional media, keyboard focus, blue controls and system light/dark preference. Project share
pages expand to 1900px with description and collaboration details side by side; below
1000px they return to an 880px single column. They link to the interactive project
screen for collaboration, roles, applications, updates and interest choices.
