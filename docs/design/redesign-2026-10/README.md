# Krug redesign, October 2026: approved mockups

Static HTML mockups approved by the owner on 12 October 2026. They replace the coral/graphite look and the deferred monochrome plan. All data in them is synthetic.

To open them, serve this folder (`python3 -m http.server`) and add query flags:

| Flag | Values |
| --- | --- |
| `theme` | `light`, `dark` |
| `lang` | `ru` (default), `en` |
| `font` | `c` (default), `a`, `b` |

`lang=en` swaps the copy through `proto-en.js`, a mockup-only helper. Inside the mockups only, fonts load from Google Fonts. The production app must self-host them.

Pages: `home.html` is the signed-in daily view; `project.html`, `event.html`, `team.html` and `profile.html` are the detail pages. `build.py` regenerates the four detail pages from `home.html`'s header. Screenshots are in `screens/`.

## Approved decisions

- **Home (signed in):**
  - Graphite header band with a short greeting and summary line.
  - A "Now and soon" strip with three tiles. The live one is wider; each tile has a countdown and a phase bar.
  - Type tabs with counts.
  - Three sections: "Looking for people" (cards with open-role slots and an Apply action), "Event calendar" (4-week timeline with a today line and a countdown per row), and "Projects, communities and people".
  - The right rail shows only "Your applications", from 1500 px up.
- **Guest home:** keeps the big headline hero, as in the earlier exploration. It is not in this folder yet.
- **Search:** lives in the header, max 30rem wide, as a light field on graphite. Dark theme uses a dark field. Below 1080 px it moves under the greeting.
- **Entity colours:**

  | Entity | Colour |
  | --- | --- |
  | project | blue |
  | team | green |
  | event | orange |
  | community | violet |
  | person | amber |

  Detail pages tint the page head with the entity colour and show a large faint monogram. Primary buttons, call-to-action panels, open slots, links and phase bars use that page's colour.
- **Button contrast:** each entity has a fill/label pair (`--c-btn`, `--c-on`) chosen for ≥4.5:1 in both themes. Global actions ("Create", home page) stay blue.
- **Dark theme:** no white slabs. Primary actions use the accent colour, call-to-action panels are tinted, and the search field is dark.
- **Covers:** the fallback is an entity-colour field with the first letter of the title. There are no decorative rings, glows or pulse animations.
- **Typography:**
  - Unbounded for large display: wordmark, page titles, greeting, section headings, timers, monograms.
  - Geologica for card and box titles.
  - Onest for UI and body text.
  - All three have Cyrillic and must be self-hosted.
- **Sizes and corners:** fluid root size `clamp(15px, 10.5px + .3vw, 20px)`. Corners are about `.55rem`, with no resting shadows.
- **Layout and languages:**
  - Layout stays fluid from 390 px to 3840 px; content width is capped at 2400 px.
  - Long Russian words wrap.
  - Russian and English layouts were both checked for overflow at 390 px and 1024 px.
