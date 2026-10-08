# Coral concept: implementation gap

Reviewed 8 October 2026 after user rejected the visual result of `c9e61ca`.
The prior functional tests passed, but they do not establish fidelity to the approved concept.

Approved reference: [coral-concept.png](design/coral-concept.png), preserved from the approved generated concept. It contains light/dark desktop and mobile views. The image is visual authority; the prior implementation is evidence of what must be replaced.

| Reference | Gap in rejected version | Acceptance condition |
|---|---|---|
| Compact single-row header | Tall header, tagline, separate action row on mobile | Keep brand, navigation, account and preferences compact; first viewport prioritizes discovery |
| Rail starts below header beside heading/search/results | Intro and search stretch across the page above filters | Desktop heading/search/tabs/results share a central column beside the rail |
| Small heading and search form one tight group | Oversized heading, wide gaps and unrelated creation actions | Match grouping, measure and relative proportions in the reference |
| Dense cards with cover, type, brief text, tags and action | Tall text-only panels stretched to the height of neighbours | Real media support, compact cards, no large empty lower halves; preserve full text on detail pages |
| Strong filter panel | One bare skill input surrounded by unused space | Group only working filters with clear labels, supported choices and visible apply/reset paths |
| Compact mobile header and early media card | Multiline header and large intro push cards downward | Search, tabs/filter access and recognizable first card appear early; preserve touch and keyboard access |
| Coherent secondary panels and varied content | Uniform project/role panels with no visual hierarchy | Use factual, available content; do not fabricate events, members or community activity |

Project covers use an additive model/schema/API/media association. Existing `save_photo` image validation and storage can be reused; post visibility and ownership must not be borrowed as project permissions. Replacing/removing covers must preserve old files on failed writes and avoid exposing private posts.

Teams independent of projects, events and communities with members/posts are agreed product work in [product-plan.md](product-plan.md), and have been implemented for verification. On 8 October the user selected the full correction together with teams, events and communities. Implementation has passed API/security tests and isolated browser flows; final visual comparison and main deployment are in progress. Native teams use owner-reviewed role applications; public communities use join/leave membership and member posts with owner moderation. Multiple teams can form around one event.

Verification for the replacement: compare approved and built light/dark desktop/mobile captures side by side for header proportions, column structure, card density, media and first-viewport composition. Then verify intermediate widths through 4K, RU/EN, keyboard, filters, actual actions, motion and fallback. Functional tests alone cannot close the visual acceptance condition.

## Implementation boundaries

Separate Team, Community and Event records; existing Project/Post capabilities stay in the modular monolith. A team can create a native project and transfer its current membership atomically. Community posts reuse the editor, photos, comments and reactions, with central public-post visibility extended to prevent private community content escaping through old routes. Public join/leave does not confer ownership. Every cover has an entity association, independent upload permissions and safe replacement cleanup.

Discovery supports all six concept types, with existing open roles accessible within teams/projects. Upcoming events come from Event records. Native creation and manual external attribution work for any safe public source URL; the source set is open. A further public source integration uses GitLab's documented public Projects API, preserving source identity/activity without inventing recruiting claims. The itch.io jam RSS URL checked during research returned HTML, so that endpoint is not treated as a supported feed.

Preview and synthetic fixture content remain isolated from the main Fedora database. Main Fedora deployment completed for application commit `15aaf50`, migration `db71e945ac30`; health and running source hashes verified. CI passed all 294 tests. Preview resources were removed after final captures.

## Verified functional correction — 8 October

The full suite passed 293 tests before the final nonempty-community deletion fix; 16 platform tests then passed with its regression. Both platform and collaboration/admin browser flows passed, alongside locale and viewport checks. Cleanup exposed the missing ORM delete dependency: post deletes now flush before the RESTRICTed community inside the same transaction, and media cleanup still follows commit. This is separate from visual acceptance.

Final concept comparison covers light/dark 1440×1000 and 390×844, plus 320px, 2560px and 3840×2160. The built screen has a compact single-row authenticated mobile header, early cover cards, a two-column desktop grid (three on ultrawide), grouped filters and factual upcoming events. Avatar/copy separation and containment are measured, images/fonts are settled before capture. Fixture copy/counts differ from the generated board and are real isolated test records; no fictitious membership or activity is shipped. Final design acceptance belongs to the user. Private-cover owner detail/editor paths and guest/non-owner denial passed for all four entity types; an existing cached tab also loaded the new versioned assets on ordinary reload.
