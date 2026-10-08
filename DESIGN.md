---
name: Krug
description: Coral and graphite collaboration discovery for people, projects, teams, events, communities and public updates.
colors:
  canvas-light: "#f5f6f8"
  paper-light: "#ffffff"
  text-light: "#242932"
  muted-light: "#596572"
  line-light: "#e7dedd"
  soft-light: "#f5e9e7"
  accent-light: "#c83f38"
  on-accent-light: "#ffffff"
  hover-light: "#a8322d"
  canvas-dark: "#181c22"
  paper-dark: "#22272f"
  text-dark: "#eff2f6"
  muted-dark: "#a4afbc"
  line-dark: "#3e3a3b"
  soft-dark: "#332c2c"
  accent-dark: "#ff786f"
  on-accent-dark: "#241111"
  hover-dark: "#ff938b"
  viewer-backdrop: "#080c12e6"
typography:
  headline:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(32px, 3vw, 46px)"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  section:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "21px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  body:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.75
  excerpt:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  share-headline:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(36px, 6vw, 52px)"
    fontWeight: 650
    lineHeight: 1.15
  discovery-headline:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(24px, 2vw, 31px)"
    fontWeight: 650
    lineHeight: 1.1
  discovery-card-title:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.25
  discovery-card-summary:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.35
  label:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 600
  metadata:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "12px"
  author:
    fontFamily: '"Krug Inter", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 600
rounded:
  text-control: "4px"
  badge: "5px"
  field: "8px"
  control: "9px"
  feedback: "10px"
  photo: "14px"
  card-mobile: "12px"
  card: "14px"
  post-card: "16px"
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
    rounded: "{rounded.post-card}"
    padding: "20px"
---

# Design System: Krug

## Overview

**Creative North Star: "A practical place to find collaborators"**

Krug helps people find collaborators through projects, teams, events, communities and opt-in profiles. Coral actions distinguish active choices against graphite or light neutral surfaces. Stories retain their responsive masonry grid, proportional photos, optional titles and readable text.

Dark is the initial theme; saved Light, Dark and System choices remain effective. Both themes share their geometry. The sticky header keeps the top-left wordmark, labelled navigation, language/theme preferences and account/write actions available while it compacts on downward scrolling and expands upward. Russian and English interface copy changes independently of user stories, names and biographies.

The shipped themes are coral light and coral dark; a standalone monochrome theme remains deferred.

**Key Characteristics:**

- Graphite and light neutral surfaces with accessible coral actions.
- Self-hosted Inter typography with a native sans-serif fallback.
- Distinct cards for people, projects, teams, events and communities; factual counts only.
- Responsive masonry cards with proportional photographs for Stories.
- Persistent preferences and a smoothly compacting sticky header.

## Colors

The shared palette pairs restrained coral with neutral surfaces; the frontmatter records the light and dark values.

### Primary

- **Accent / On accent:** coral primary buttons, active navigation, selection and feedback. Light-mode coral uses white labels; brighter dark-mode coral uses dark labels to preserve contrast. The circular brand mark and active underline use Accent; primary hover uses Hover.

### Neutral

- **Canvas:** page and solid sticky-header background.
- **Paper:** post cards, forms, settings/authentication cards, theme disclosure and mobile bottom navigation.
- **Text:** story copy, authors and primary headings.
- **Muted:** metadata, introductions, hints and inactive navigation.
- **Line:** one-pixel card borders, discussion dividers and secondary hover fill.
- **Soft:** secondary controls, selected likes, avatar discs, badges, photo backdrop and mobile active navigation.
- **Viewer backdrop:** a dark translucent overlay behind the modal photo in both themes.

The live CSS variables `--canvas`, `--paper`, `--text`, `--muted`, `--line`, `--soft`, `--accent`, `--on-accent` and `--hover` map to the corresponding light values at the root and dark values under `data-theme="dark"`. Frontmatter component variants use the light baseline unless explicitly labelled dark.

**The Coral Action Rule.** Use coral for actions and active state; let neutral surfaces frame user content and retain photographs in their original colors.

## Typography

**Interactive app font:** the locally hosted Inter variable font with a native sans-serif fallback. It is served from the app and includes its license in `frontend/INTER-LICENSE.txt`; there is no third-party font request. Font synthesis is disabled. Static public share pages use the system sans-serif stack declared in `frontend/share.css`.

### Hierarchy

- **App headline:** regular route headings use `clamp(32px, 3vw, 46px)` and become (34px) on narrow screens. Public share headlines use `clamp(36px, 6vw, 52px)`.
- **Story title and excerpt:** story links use (22px), increasing to (23px) on mobile; excerpts use (16px), preserve newlines and cap at (75ch). Full story copy uses (18px), reducing to (17px) on mobile, preserves newlines and stays within (70ch).
- **Discovery hierarchy:** the compact discovery heading uses `clamp(24px, 2vw, 31px)` on desktop, (22–29px) through tablet widths and (21–27px) on phones. Card titles use (17px) with (14px) summaries. These compact discovery sizes are separate from the story scale.
- **Section:** app section headings use (21px), reducing to (20px) on mobile. Public share section headings use (24px).
- **Label:** compact action controls; field labels use weight (550). General introductions use (16px), line-height (1.6) and maximum width (65ch), reducing to (15px) on mobile. Discovery introductions use (15px) desktop and (12px) on narrow screens.
- **Metadata:** dates use tabular numerals and sit below the author beside a two-row avatar; size is (12px). Author names retain (14px) and weight (600), separating identity from the quieter date. Hints use (13px) and line-height (1.55).
- **Metadata:** dates use tabular numerals and sit below the author beside a two-row avatar; size is (12px). Author names retain (14px) and weight (600), separating identity from the quieter date. Hints use (13px) and line-height (1.55).

The native sans-serif wordmark uses (26px), weight (750) and tracking (-0.03em), reducing to (22px) on mobile and (20px) at the narrowest breakpoint. It is an identity treatment, not the page heading.

**The Reading First Rule.** Keep stories readable without photographs, preserve user line breaks and allow long text to wrap.

## Layout

The desktop shell uses a centered width `min(calc(100% - 64px), 3600px)`. Discovery caps at (2060px) on ordinary desktop widths and up to (2200px) on ultrawide screens; project detail and updates remain capped at (1800px). Story/feed pages retain the broad shell. Page vertical padding is (44px) above and (96px) below.

Post listings use CSS Grid with `repeat(auto-fill, minmax(min(100%, 350px), 1fr))`, (8px) automatic rows, default row flow and (24px) gaps. Card heights follow their intrinsic contents, including photo loading, wrapping text and changing reaction controls. Native ResizeObserver measures each inner card and updates its outer grid span; the observer is disconnected before each screen render. Cards keep DOM and keyboard order from the paginated response. Default row flow places cards in that sequence, while differing card heights prevent a uniform visual row rhythm. The first request loads up to (24) items; Load more appends the next page. Scrolling alone does not fetch another page.

Listing photos appear after the author and before the optional title and text. Full posts retain heading, optional photo and full text order; an untitled full post has a visually hidden Post heading rather than an invented visible title. Text-only cards retain the same controls and reading path.

At (1700px) and above, the header uses three columns with equal flexible sides: the brand stays left, navigation occupies the center and grouped preferences/account actions stay right. Tablet and mobile retain their compact navigation patterns. Search spans the available feed container instead of a separate narrow cap.

The sticky header keeps controls and focused elements in the same DOM. The current compact shell uses a (64px) desktop header and a (62px) header at widths up to (850px); narrow layouts move the four primary destinations to the fixed bottom navigation. Header and tagline transitions use `cubic-bezier(.16, 1, .3, 1)`; reduced motion disables them.

At (650px) and below, the header stays one row and the fixed bottom navigation carries the four primary destinations. General content uses the full width, (20px) side padding and bottom clearance `calc(100px + env(safe-area-inset-bottom))`; discovery overrides its top and side spacing to stay compact. Story search moves the language select to a second full-width row; ordinary fields use (16px) text while this select uses (13px). Search labels remain accessible while visually hidden. Toasts clear the bottom navigation and safe area. At (360px) and below, header side padding becomes (9px).

At mobile widths, project, person and role cards become one column with (16px) gaps; the Stories masonry grid also becomes one column. Authentication forms cap at (490px). Tabs, statistics and action controls wrap.

## Elevation & Depth

Post cards and form/settings/authentication containers use Paper and one-pixel Line borders. Cards remain flat at rest; their different heights come from content rather than fixed image crops. The header and bottom navigation remain solid. The only box shadows belong to transient toasts: `0 8px 28px #2429321a` in light mode and `0 8px 28px #00000033` in dark mode.

**The Flat Surface Rule.** Separate resting content with cool surfaces and dividers; reserve the shipped shadow for transient toast feedback.

## Shapes

Fields, tabs and mobile navigation use the field radius; primary controls use the control radius. Form/settings cards use the card radius, reduced on mobile. Post cards use a distinct (16px) radius at every width. Photos use the photo radius; toasts and editor previews use the feedback radius. Status badges have the badge radius. Avatars are circular (32px), with a profile variant (72px). The top-left brand mark is a circular Accent outline (26px with 5px border; mobile 22px with 6px border). Interface SVG icons use (20px) dimensions, with a filled heart for liked state.

## Components

### Buttons

Primary actions use Accent/On accent, minimum height (44px) and compact padding. Secondary/liked controls use Soft/Text. Destructive actions are transparent with a Muted border and gain Accent/On accent on fine-pointer hover. Text actions remain transparent and underline on hover. Disabled buttons show wait cursor and opacity (0.55); pressed controls scale to (0.98).

Transform/background transitions use (150ms ease-out). Fine-pointer hover avoids sticky touch states. Keyboard focus uses a (2px) Muted outline with (4px) offset for controls, links and fields.

### Cards / Containers

Post cards carry a (32px) circular avatar spanning two metadata rows, an author name, date, optional photo, optional title, linked excerpt and wrapping interaction toolbar. Inner padding is (20px), reduced to (18px) on mobile. Excerpts show up to (260) characters with an ellipsis and Read more when needed. Titles are omitted when empty; text links to the full post and the photo opens its viewer. Form/settings cards use Paper, Line borders and padding (24px; 18px mobile). Authentication card padding is (28px desktop; 20px mobile). Empty states use a solid Line border, Paper background and card-radius corners with centered copy and an action when available.

### Inputs / Fields

Native inputs, selects and resizable textareas use Paper/Text, a Line border and minimum height (44px). Placeholders use Muted at full opacity. Focus shifts the border to Accent while retaining the keyboard outline. Textareas have minimum height (110px), or (310px) in the story editor. Native checkboxes use Accent and (18px) dimensions; their labelled row remains at least (44px) tall.

Search uses a quiet Paper field with an initially transparent border and an Accent focus border. Its visible hierarchy comes from the query, language select and submit action; labels and explanatory text remain available to assistive technology without adding a second visible label row.

### Navigation and tabs

Desktop navigation combines inline SVG icons and labels at (14px), weight (550), minimum height (46px) and padding (10px). Active destinations use Text with an Accent bottom border; inactive fine-pointer hover uses Soft/Text. Mobile stacks icons above (10px) labels, adds field-radius corners and uses Soft/Text active fill. Current destinations expose `aria-current="page"`. Discovery tabs use (13px) type and an Accent underline; shared feed tabs retain their filled active state.

### Badges and feedback

Draft/status badges are non-interactive Soft/Muted annotations at (11px). Errors and success messages use explicit text on Soft; errors also have a Muted border. Loading uses readable status copy with a (16px), one-second linear spinner. Toasts use Accent/On accent, the toast shadow and (180ms ease-out) opacity. Feedback is announced through `role="status"` and `aria-live="polite"`.

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

- **Do** use shared theme variables and the recorded coral/graphite palette.
- **Do** use simple native sans-serif headings, reading text and controls.
- **Do** preserve proportional photographs and readable text-only posts at every width.
- **Do** allow an empty title without introducing a synthetic visible heading.
- **Do** keep labelled navigation, account/write actions and preference controls reachable during header compaction.
- **Do** retain visible keyboard focus, wrapping text and reduced-motion behavior.
- **Do** clear mobile bottom navigation with safe-area padding.

### Don't:

- **Don't** replace the established graphite and coral palette with pastel accents.
- **Don't** stretch photographs to grid height, force square crops or make stories depend on an image.
- **Don't** translate user stories, names or biographies with interface copy.
- **Don't** extend the toast shadow into resting post cards or add cinematic motion.

Documentation is derived from the current frontend source. Temporary synthetic review content is verification evidence, not shipping imagery or product copy.


## Project discovery and sharing

Collaboration discovery uses coral and graphite, with light and dark accent/text
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
proportional media, keyboard focus, coral controls and system light/dark preference. Project share
pages expand to 1900px with description and collaboration details side by side; below
1000px they return to an 880px single column. They link to the interactive project
screen for collaboration, roles, applications, updates and interest choices.
