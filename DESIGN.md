---
name: Krug
description: Compact social reading with cold graphite, blue actions and simple sans-serif typography.
colors:
  canvas-light: "#edf1f4"
  paper-light: "#ffffff"
  text-light: "#172d3b"
  muted-light: "#476071"
  line-light: "#b9cbd7"
  soft-light: "#dce7ee"
  accent-light: "#17649b"
  on-accent-light: "#ffffff"
  hover-light: "#105381"
  canvas-dark: "#151c21"
  paper-dark: "#1c252c"
  text-dark: "#e6edf2"
  muted-dark: "#a4b5c1"
  line-dark: "#354651"
  soft-dark: "#26343e"
  accent-dark: "#246f9f"
  on-accent-dark: "#ffffff"
  hover-dark: "#1e608b"
typography:
  headline:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(28px, 2vw, 36px)"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(22px, 1.3vw, 28px)"
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: "-0.02em"
  section:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "21px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  body:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.8
  excerpt:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "clamp(15px, .85vw, 19px)"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 600
  metadata:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "12px"
rounded:
  text-control: "4px"
  badge: "5px"
  field: "8px"
  control: "9px"
  photo: "10px"
  card-mobile: "12px"
  card: "14px"
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
  story-row:
    textColor: "{colors.text-light}"
    padding: "24px 0"
---

# Design System: Krug

## Overview

**Creative North Star: "Compact social reading"**

Krug combines a compact social feed with the quieter pace of an author journal. Cold graphite and a restrained saturated blue frame real stories; Native sans-serif titles keep the interface simple and familiar. Flat chronological rows, readable copy and proportional photographs replace the former monochrome card feed.

Dark is the initial theme; saved Light, Dark and System choices remain effective. Both themes share their geometry. The sticky header keeps the top-left wordmark, labelled navigation, language/theme preferences and account/write actions available while it compacts on downward scrolling and expands upward. Russian and English interface copy changes independently of user stories, names and biographies.

**Key Characteristics:**

- Cold graphite surfaces and restrained blue actions.
- Native sans-serif titles, reading text and controls.
- Broad responsive story rows with optional proportional photographs.
- Persistent preferences and a smoothly compacting sticky header.

## Colors

The palette uses cool neutral surfaces with a saturated blue action accent; the frontmatter records the actual light and dark values.

### Primary

- **Accent / On accent:** blue-and-white primary buttons, active tabs, selection and toast feedback. The circular brand mark and active desktop navigation underline use Accent; primary hover uses Hover.

### Neutral

- **Canvas:** page and solid sticky-header background.
- **Paper:** forms, settings/authentication cards, preference controls and mobile bottom navigation.
- **Text:** story copy, authors and primary headings.
- **Muted:** metadata, introductions, hints and inactive navigation.
- **Line:** one-pixel row dividers, card borders and secondary hover fill.
- **Soft:** secondary controls, selected likes, avatar discs, badges, photo backdrop and mobile active navigation.

The live CSS variables `--canvas`, `--paper`, `--text`, `--muted`, `--line`, `--soft`, `--accent`, `--on-accent` and `--hover` map to the corresponding light values at the root and dark values under `data-theme="dark"`. Frontmatter component variants use the light baseline unless explicitly labelled dark.

**The Blue Action Rule.** Use blue for actions and active state; let cool neutrals frame user content and retain photographs in their original colors.

## Typography

**Font throughout:** the native sans-serif stack in the frontmatter. Headings use weight 650; font synthesis is disabled. No font download is required.

### Hierarchy

- **Headline:** native sans-serif page heading, balanced wrapping and negative tracking; mobile overrides size to (27px). Route headings identify Feed or Discover instead of repeating the wordmark.
- **Title:** native sans-serif story links; maximum line length (45ch), with mobile size (23px).
- **Section:** native sans-serif section headings; mobile size (20px). Rail headings use (17px).
- **Body:** full story copy preserves newlines, wraps long strings and stays within (70ch).
- **Excerpt:** responsive feed previews use Text rather than Muted, preserve newlines and cap at (75ch).
- **Label:** compact action controls; field labels use weight (550). Introductions use (14px), line-height (1.65) and maximum width (65ch).
- **Metadata:** author/date rows wrap and use tabular numerals; mobile size (11px). Hints use (13px) and line-height (1.55).

The native sans-serif wordmark uses (26px), weight (750) and tracking (-0.03em), reducing to (22px) on mobile and (20px) at the narrowest breakpoint. It is an identity treatment, not the page heading.

**The Reading First Rule.** Keep stories readable without photographs, preserve user line breaks and allow long text to wrap.

## Layout

The desktop shell uses a centered width `min(92vw, 2800px)`. Feed and Discover pair a flexible story column with a contextual rail sized `clamp(260px, 19vw, 360px)` and gap `clamp(36px, 4vw, 120px)`. Other routes cap their width at (1040px). Page vertical padding is (28px) above and (80px) below; line-length limits remain independent of the broad container.

At (1199px) and below, the rail disappears and Feed/Discover become one column capped at (1100px). Photos remain below story copy at every width, aligned with its left edge, capped at (960px) wide and (540px) high without cropping. Text-only stories retain the same reading order and constrained line lengths.

The sticky header reserves its expanded height in the layout while its inner surface compacts; controls and focused elements remain in the same DOM. Desktop expanded/compact minimum heights are (108px / 72px). From (651px) through (1499px), navigation occupies a second header row and heights become (152px / 124px). Through (1000px), account/write actions occupy a third row and heights become (202px / 174px). Header padding and minimum height transition with (280ms) using `cubic-bezier(.16, 1, .3, 1)`; tagline max-height uses the same motion and opacity uses (180ms ease-out). Below scroll position (80px) the header expands; direction changes of at least (12px) determine compact state beyond that point.

At (650px) and below, the header uses two rows with expanded/compact heights (132px / 108px), and the tagline is hidden. Navigation becomes a fixed labelled bottom bar. Main content uses full width, side padding (16px) and bottom clearance `calc(100px + env(safe-area-inset-bottom))`. Search moves the language field to a second full-width row; ordinary fields use (16px) text while the compact language button uses (13px). Toasts clear the bottom navigation and safe area. At (360px) and below, header side padding becomes (10px).

Authentication forms cap at (490px). Metadata, tabs, statistics and action controls wrap. The context rail is sticky at (124px) on desktop, or (168px) within the intermediate header range.

## Elevation & Depth

The feed is flat: transparent story rows use bottom Line dividers, while forms/settings/authentication containers use Paper and one-pixel borders. The header and bottom navigation remain solid. The only box shadows belong to transient toasts: `0 8px 28px #172d3b1a` in light mode and `0 8px 28px #00000033` in dark mode.

**The Flat Surface Rule.** Separate resting content with cool surfaces and dividers; reserve the shipped shadow for transient toast feedback.

## Shapes

Fields, tabs and mobile navigation use the field radius; primary controls use the control radius. Form/settings cards use the card radius, reduced on mobile. Story rows have no enclosing card silhouette. Photos and toasts share the photo radius. Status badges have the badge radius. Avatars are circular (32px), with a profile variant (72px). The top-left brand mark is a circular Accent outline (26px with 7px border; mobile 22px with 6px border). Interface SVG icons use (20px) dimensions, with a filled heart for liked state.

## Components

### Buttons

Primary actions use blue fill, white labels, minimum height (44px) and compact padding. Secondary/liked controls use Soft/Text. Destructive actions are transparent with a Muted border and gain Accent/On accent on fine-pointer hover. Text actions remain transparent and underline on hover. Disabled buttons show wait cursor and opacity (0.55); pressed controls scale to (0.98).

Transform/background transitions use (150ms ease-out). Fine-pointer hover avoids sticky touch states. Keyboard focus uses a (2px) Muted outline with (4px) offset for controls, links and fields.

### Cards / Containers

Story rows carry a wrapping author/date row, title, excerpt, optional photo and a separate wrapping action toolbar. They use bottom dividers and padding (24px 0), reduced to (20px 0) on mobile. Form/settings cards use Paper, Line borders and padding (24px; 18px mobile). Authentication card padding is (28px desktop; 20px mobile). Empty states use a dashed Line border with centered copy and an action when available.

### Inputs / Fields

Native inputs, selects and resizable textareas use Paper/Text, a Line border and minimum height (44px). Placeholders use Muted at full opacity. Focus shifts the border to Accent while retaining the keyboard outline. Textareas have minimum height (110px), or (310px) in the story editor. Native checkboxes use Accent and (18px) dimensions; their labelled row remains at least (44px) tall.

### Navigation and tabs

Desktop navigation combines inline SVG icons and labels at (14px), weight (550), minimum height (46px) and padding (10px). Active destinations use Text with an Accent bottom border; inactive fine-pointer hover uses Soft/Text. Mobile stacks icons above (10px) labels, adds field-radius corners and uses Soft/Text active fill. Current destinations expose `aria-current="page"`. Tabs use (13px) type, field-radius corners and Accent/On accent active fill.

### Feed context rail

Flat sections use bottom dividers, section headings and explanatory text rather than additional cards. Author rows combine a circular initial avatar with a wrapping name, minimum height (48px), field-radius corners and Soft hover fill. Authors come from loaded stories, with deduplicated profile links, no signed-in author and at most six other authors. The writing section links to a new story or registration for anonymous readers. The rail disappears below (1200px).

### Badges and feedback

Draft/status badges are non-interactive Soft/Muted annotations at (11px). Errors and success messages use explicit text on Soft; errors also have a Muted border. Loading uses readable status copy with a (16px), one-second linear spinner. Toasts use Accent/On accent, the toast shadow and (180ms ease-out) opacity. Feedback is announced through `role="status"` and `aria-live="polite"`.

### Photographs

Photos use automatic width and height, maximum width (100%), `object-fit: contain`, and top/start alignment. They retain intrinsic proportions rather than filling a prescribed frame or grid-row height. Feed maximum height is (540px desktop; 450px mobile); article maximum is (680px desktop), with the mobile feed limit overriding it. Editor previews cap at (280px). Optional photos do not determine whether text-only stories remain useful.

### Preferences and motion

A RU/EN button shows the current language and names the target language for assistive technology. The theme icon opens a native details disclosure with labelled Light, Dark and System buttons, pressed state, Escape handling and focus return. Both controls remain reachable in every header state. Theme changes apply without replacing the screen; language changes preserve active form content and selected photos. Reduced-motion preference disables transitions and animations, including header motion, while retaining readable loading status.

## Do's and Don'ts

### Do:

- **Do** use shared theme variables and the recorded cold blue/graphite palette.
- **Do** use simple native sans-serif headings, reading text and controls.
- **Do** preserve proportional photographs and readable text-only stories at every width.
- **Do** keep labelled navigation, account/write actions and preference controls reachable during header compaction.
- **Do** retain visible keyboard focus, wrapping text and reduced-motion behavior.
- **Do** clear mobile bottom navigation with safe-area padding.

### Don't:

- **Don't** restore the rejected monochrome card feed, pastel palette or narrow desktop feed.
- **Don't** stretch photographs to grid height, force square crops or make stories depend on an image.
- **Don't** translate user stories, names or biographies with interface copy.
- **Don't** extend the toast shadow into resting story rows or add cinematic motion.

Documentation is derived from the current frontend source. Temporary synthetic review content is verification evidence, not shipping imagery or product copy.

## Post interactions

Listing cards place Like and labelled Comments together below the photo or text, before reading/edit actions. Likes use the existing API and show confirmed count/state; unavailable counts offer retry. The full post uses the same like control. Discussion lives inside the article below its action toolbar; comment metadata stays grouped and only delete moves to the far edge. Comments links scroll to discussion with clearance for the sticky header.
