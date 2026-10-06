---
name: Krug
description: Developer project discovery with graphite surfaces, a filter sidebar, blue actions and public project updates.
colors:
  canvas-light: "#f5f6f8"
  paper-light: "#ffffff"
  text-light: "#242932"
  muted-light: "#596572"
  line-light: "#dfe3e9"
  soft-light: "#e9edf2"
  accent-light: "#2368a4"
  on-accent-light: "#ffffff"
  hover-light: "#19578c"
  canvas-dark: "#181c22"
  paper-dark: "#22272f"
  text-dark: "#eff2f6"
  muted-dark: "#a4afbc"
  line-dark: "#343c47"
  soft-dark: "#2c3541"
  accent-dark: "#2876bc"
  on-accent-dark: "#ffffff"
  hover-dark: "#2266a5"
  viewer-backdrop: "#080c12e6"
typography:
  headline:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(32px, 3vw, 46px)"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  section:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "21px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  body:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.75
  excerpt:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 600
  metadata:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "12px"
  author:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
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

**Creative North Star: "A masonry social feed"**

Krug presents posts in a Pinterest-like responsive masonry grid. Graphite surfaces, restrained blue actions and native sans-serif text keep the interface familiar. Each card starts with its author, followed by a proportional photo when supplied, an optional title and readable text. The interface supports browsing and conversation without becoming a marketing page.

Dark is the initial theme; saved Light, Dark and System choices remain effective. Both themes share their geometry. The sticky header keeps the top-left wordmark, labelled navigation, language/theme preferences and account/write actions available while it compacts on downward scrolling and expands upward. Russian and English interface copy changes independently of user stories, names and biographies.

**Key Characteristics:**

- Cold graphite surfaces and restrained blue actions.
- Native sans-serif titles, reading text and controls.
- Responsive masonry cards with proportional photographs and optional titles.
- Persistent preferences and a smoothly compacting sticky header.

## Colors

The palette uses cool neutral surfaces with a saturated blue action accent; the frontmatter records the actual light and dark values.

### Primary

- **Accent / On accent:** blue-and-white primary buttons, active tabs, selection and toast feedback. The circular brand mark and active desktop navigation underline use Accent; primary hover uses Hover.

### Neutral

- **Canvas:** page and solid sticky-header background.
- **Paper:** post cards, forms, settings/authentication cards, theme disclosure and mobile bottom navigation.
- **Text:** story copy, authors and primary headings.
- **Muted:** metadata, introductions, hints and inactive navigation.
- **Line:** one-pixel card borders, discussion dividers and secondary hover fill.
- **Soft:** secondary controls, selected likes, avatar discs, badges, photo backdrop and mobile active navigation.
- **Viewer backdrop:** a dark translucent overlay behind the modal photo in both themes.

The live CSS variables `--canvas`, `--paper`, `--text`, `--muted`, `--line`, `--soft`, `--accent`, `--on-accent` and `--hover` map to the corresponding light values at the root and dark values under `data-theme="dark"`. Frontmatter component variants use the light baseline unless explicitly labelled dark.

**The Blue Action Rule.** Use blue for actions and active state; let cool neutrals frame user content and retain photographs in their original colors.

## Typography

**Font throughout:** the native sans-serif stack in the frontmatter. Page and section headings use weight 650; story titles and authors use 600. Font synthesis is disabled. No font download is required.

### Hierarchy

- **Headline:** native sans-serif page heading, balanced wrapping and negative tracking; mobile overrides size to (34px). Route headings identify Feed or Discover instead of repeating the wordmark.
- **Title:** native sans-serif story links; maximum line length (45ch), with mobile size (23px).
- **Section:** native sans-serif section headings; mobile size (20px).
- **Body:** full story copy preserves newlines, wraps long strings and stays within (70ch); mobile size is (17px).
- **Excerpt:** feed previews use Text rather than Muted, preserve newlines and cap at (75ch); mobile size is (16px).
- **Label:** compact action controls; field labels use weight (550). Introductions use (16px), line-height (1.6) and maximum width (65ch), reducing to (15px) on mobile.
- **Metadata:** dates use tabular numerals and sit below the author beside a two-row avatar; size is (12px). Author names retain (14px) and weight (600), separating identity from the quieter date. Hints use (13px) and line-height (1.55).

The native sans-serif wordmark uses (26px), weight (750) and tracking (-0.03em), reducing to (22px) on mobile and (20px) at the narrowest breakpoint. It is an identity treatment, not the page heading.

**The Reading First Rule.** Keep stories readable without photographs, preserve user line breaks and allow long text to wrap.

## Layout

The desktop shell uses a centered width `min(calc(100% - 64px), 3600px)`: (32px) on each side until the width cap takes over. Feed and Discover occupy this broad shell without a context rail. Other routes cap their width at (1000px). Page vertical padding is (44px) above and (96px) below.

Post listings use CSS Grid with `repeat(auto-fill, minmax(min(100%, 350px), 1fr))`, (8px) automatic rows, default row flow and (24px) gaps. Card heights follow their intrinsic contents, including photo loading, wrapping text and changing reaction controls. Native ResizeObserver measures each inner card and updates its outer grid span; the observer is disconnected before each screen render. Cards keep DOM and keyboard order from the paginated response. Default row flow places cards in that sequence, while differing card heights prevent a uniform visual row rhythm. The first request loads up to (24) items; Load more appends the next page. Scrolling alone does not fetch another page.

Listing photos appear after the author and before the optional title and text. Full posts retain heading, optional photo and full text order; an untitled full post has a visually hidden Post heading rather than an invented visible title. Text-only cards retain the same controls and reading path.

At (1700px) and above, the header uses three columns with equal flexible sides: the brand stays left, navigation occupies the center and grouped preferences/account actions stay right. Tablet and mobile retain their existing row layouts. Search spans the available feed container instead of a separate narrow cap.

The sticky header reserves its expanded height in the layout while its inner surface compacts; controls and focused elements remain in the same DOM. Desktop expanded/compact minimum heights are (92px / 72px). From (651px) through (1399px), navigation occupies a second header row and heights become (128px / 112px). Between (651px) and (1000px), the account becomes an avatar and the signed-in compose action becomes a (44px) icon control; accessible names remain present, and navigation uses (12px) labels. Header padding and minimum height transition with (280ms) using `cubic-bezier(.16, 1, .3, 1)`; tagline max-height uses the same motion and opacity uses (180ms ease-out). Below scroll position (80px) the header expands; direction changes of at least (12px) determine compact state beyond that point.

At (650px) and below, the header uses two rows with expanded/compact heights (120px / 104px), and the tagline is hidden. Navigation becomes a fixed labelled bottom bar. Main content uses full width, top padding (28px), side padding (20px) and bottom clearance `calc(100px + env(safe-area-inset-bottom))`. Search moves the language select to a second full-width row; ordinary fields use (16px) text while this select uses (13px). Search labels remain accessible while visually hidden. Toasts clear the bottom navigation and safe area. At (360px) and below, header side padding becomes (10px).

At mobile widths, the masonry grid becomes one column with (16px) gaps. Authentication forms cap at (490px). Tabs, statistics and action controls wrap.

## Elevation & Depth

Post cards and form/settings/authentication containers use Paper and one-pixel Line borders. Cards remain flat at rest; their different heights come from content rather than fixed image crops. The header and bottom navigation remain solid. The only box shadows belong to transient toasts: `0 8px 28px #2429321a` in light mode and `0 8px 28px #00000033` in dark mode.

**The Flat Surface Rule.** Separate resting content with cool surfaces and dividers; reserve the shipped shadow for transient toast feedback.

## Shapes

Fields, tabs and mobile navigation use the field radius; primary controls use the control radius. Form/settings cards use the card radius, reduced on mobile. Post cards use a distinct (16px) radius at every width. Photos use the photo radius; toasts and editor previews use the feedback radius. Status badges have the badge radius. Avatars are circular (32px), with a profile variant (72px). The top-left brand mark is a circular Accent outline (26px with 5px border; mobile 22px with 6px border). Interface SVG icons use (20px) dimensions, with a filled heart for liked state.

## Components

### Buttons

Primary actions use blue fill, white labels, minimum height (44px) and compact padding. Secondary/liked controls use Soft/Text. Destructive actions are transparent with a Muted border and gain Accent/On accent on fine-pointer hover. Text actions remain transparent and underline on hover. Disabled buttons show wait cursor and opacity (0.55); pressed controls scale to (0.98).

Transform/background transitions use (150ms ease-out). Fine-pointer hover avoids sticky touch states. Keyboard focus uses a (2px) Muted outline with (4px) offset for controls, links and fields.

### Cards / Containers

Post cards carry a (32px) circular avatar spanning two metadata rows, an author name, date, optional photo, optional title, linked excerpt and wrapping interaction toolbar. Inner padding is (20px), reduced to (18px) on mobile. Excerpts show up to (260) characters with an ellipsis and Read more when needed. Titles are omitted when empty; text links to the full post and the photo opens its viewer. Form/settings cards use Paper, Line borders and padding (24px; 18px mobile). Authentication card padding is (28px desktop; 20px mobile). Empty states use a solid Line border, Paper background and card-radius corners with centered copy and an action when available.

### Inputs / Fields

Native inputs, selects and resizable textareas use Paper/Text, a Line border and minimum height (44px). Placeholders use Muted at full opacity. Focus shifts the border to Accent while retaining the keyboard outline. Textareas have minimum height (110px), or (310px) in the story editor. Native checkboxes use Accent and (18px) dimensions; their labelled row remains at least (44px) tall.

Search uses a quiet Paper field with an initially transparent border and an Accent focus border. Its visible hierarchy comes from the query, language select and submit action; labels and explanatory text remain available to assistive technology without adding a second visible label row.

### Navigation and tabs

Desktop navigation combines inline SVG icons and labels at (14px), weight (550), minimum height (46px) and padding (10px). Active destinations use Text with an Accent bottom border; inactive fine-pointer hover uses Soft/Text. Mobile stacks icons above (10px) labels, adds field-radius corners and uses Soft/Text active fill. Current destinations expose `aria-current="page"`. Tabs use (13px) type, field-radius corners and Accent/On accent active fill.

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

- **Do** use shared theme variables and the recorded cold blue/graphite palette.
- **Do** use simple native sans-serif headings, reading text and controls.
- **Do** preserve proportional photographs and readable text-only posts at every width.
- **Do** allow an empty title without introducing a synthetic visible heading.
- **Do** keep labelled navigation, account/write actions and preference controls reachable during header compaction.
- **Do** retain visible keyboard focus, wrapping text and reduced-motion behavior.
- **Do** clear mobile bottom navigation with safe-area padding.

### Don't:

- **Don't** replace the established graphite and blue palette with pastel accents.
- **Don't** stretch photographs to grid height, force square crops or make stories depend on an image.
- **Don't** translate user stories, names or biographies with interface copy.
- **Don't** extend the toast shadow into resting post cards or add cinematic motion.

Documentation is derived from the current frontend source. Temporary synthetic review content is verification evidence, not shipping imagery or product copy.


## Project discovery and sharing

The approved v0.1 primary surface is project discovery, preserving cold graphite,
blue actions and native sans-serif typography. The main header links Projects,
Stories, Saved, My projects and Settings; signed-in Stories exposes the preserved
author feed, own posts, connections and post editor.

Discovery uses a 1480px maximum shell with a 240px desktop filter sidebar and
compact project cards in an adaptive grid. At 850px and below the sidebar becomes
search plus native collapsible filters. Cards show actual title, summary, source,
status, tags/skills and stage; no fabricated audience, team or growth figures.
Tag and skill links use their respective structured search filters.

Project details separate the description from the account action panel. Save,
Follow and Interested can be selected together. Interest visibility requires a
separate per-project checkbox, initially off and disabled until Interested is
selected. Public profile lists include only explicit opt-ins. Public share links
are available only for published projects; drafts stay inside the authenticated
app. Updates reuse the existing post editor, photos and discussion UI.

The project grid has one brief 220ms opacity/6px entrance; links use a 180ms
arrow translation and buttons retain 150ms press feedback. Header and toast
transitions preserve the existing stable DOM. Reduced-motion disables animation
and transition; no motion library or scroll choreography.

Public HTML pages use share.css with readable 800px measure, native typography,
proportional media, keyboard focus and system light/dark preference. They link to
the interactive project screen for saved/followed/interest choices.
