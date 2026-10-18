"""Fill an empty Krug instance with invented demo data for README screenshots.

Usage: python seed_readme_preview.py BASE_URL
Run inside the web container: stdlib urllib plus Pillow only.
Runs only where PUBLIC_APP_URL is the isolated preview, and refuses when public
listings already return content (private accounts are not visible to that check).
"""
import io
import json
import math
import os
import random
import sys
import zlib
from datetime import datetime, timedelta, timezone
from urllib import error, request

from PIL import Image, ImageDraw, ImageFilter

BASE = ""
PASSWORD = "readme-demo-pass-2026"
PREVIEW_URL = "http://127.0.0.1:18103"
DARK = (15, 23, 42)
COLORS = {
    "blue": (37, 99, 235), "teal": (13, 148, 136), "red": (220, 38, 38), "purple": (126, 34, 206),
    "amber": (217, 119, 6), "violet": (109, 40, 217), "coral": (244, 114, 96),
}
# Start of the current UTC hour; event dates are offsets from it.
NOW = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def at(days, hours=0):
    return (NOW + timedelta(days=days, hours=hours)).isoformat()


def call(method, path, token=None, body=None, raw=None):
    """Return decoded JSON (None for empty bodies); raise on any non-2xx status."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        headers["Content-Type"] = "image/jpeg"
    req = request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=60) as response:
            status, payload = response.status, response.read()
    except error.HTTPError as exc:
        status, payload = exc.code, exc.read()
    if not 200 <= status < 300:
        raise SystemExit(f"{method} {path} failed with {status}: {payload[:300].decode(errors='replace')}")
    return json.loads(payload) if payload else None


# Procedural art: deterministic per key, no people, logos or third-party assets.
def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b, strict=True))


def draw_grid(d, w, h, c, rng):
    cell = max(w, h) // 24
    for x in range(0, w, cell):
        for y in range(0, h, cell):
            if rng.random() < 0.35:
                d.rectangle([x + 4, y + 4, x + cell - 4, y + cell - 4], fill=mix(DARK, c, rng.uniform(0.5, 1)))


def draw_waves(d, w, h, c, rng):
    for k in range(18):
        base = h * k / 18
        points = [(x, base + 40 * ((k % 4) + 1) / 4 * math.sin(x / (90 + k * 3) + k))
                  for x in range(0, w + 1, 8)]
        d.line(points, fill=mix(DARK, c, 0.3 + 0.7 * k / 18), width=6)


def draw_orbit(d, w, h, c, rng):
    cx, cy = w / 2, h / 2
    d.ellipse([cx - 60, cy - 60, cx + 60, cy + 60], fill=c)
    for r_scale in (0.3, 0.5, 0.7, 0.9):
        r = min(w, h) * r_scale / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=mix(DARK, c, 0.5), width=4)
        for _ in range(3):
            angle = rng.uniform(0, 6.283)
            px, py = cx + r * math.cos(angle), cy + r * math.sin(angle)
            d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=c)


def draw_constellation(d, w, h, c, rng):
    points = [(rng.uniform(40, w - 40), rng.uniform(40, h - 40)) for _ in range(40)]
    for i, (x1, y1) in enumerate(points):
        for x2, y2 in points[i + 1:]:
            if (x1 - x2) ** 2 + (y1 - y2) ** 2 < 220 ** 2:
                d.line([(x1, y1), (x2, y2)], fill=mix(DARK, c, 0.4), width=2)
    for x, y in points:
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=c)


def draw_bars(d, w, h, c, rng):
    bar = w / 20
    for i in range(16):
        top = h * rng.uniform(0.25, 0.85)
        x = w * 0.1 + i * bar
        d.rectangle([x, top, x + bar * 0.7, h * 0.9], fill=c)
        d.rectangle([x, top, x + bar * 0.7, top + 8], fill=mix(c, (255, 255, 255), 0.4))


STYLES = {"grid": draw_grid, "waves": draw_waves, "orbit": draw_orbit,
          "constellation": draw_constellation, "bars": draw_bars}


def picture(style, color, size, key):
    """JPEG bytes for a deterministic abstract image; key fixes the random seed."""
    rng = random.Random(zlib.crc32(key.encode()))
    w, h = size
    if style == "gradient":
        mask = Image.linear_gradient("L").rotate(rng.choice((0, 45, 90)), expand=False).resize(size)
        mask = mask.filter(ImageFilter.GaussianBlur(max(w, h) // 8))
        img = Image.composite(Image.new("RGB", size, COLORS[color]), Image.new("RGB", size, DARK), mask)
    else:
        img = Image.new("RGB", size, DARK)
        STYLES[style](ImageDraw.Draw(img), w, h, COLORS[color], rng)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


AVATARS = [("orbit", "blue"), ("bars", "teal"), ("grid", "red"), ("waves", "purple"),
           ("gradient", "amber"), ("constellation", "violet")]

USERS = [
    {"username": "sofia_l", "display_name": "Sofia Lindqvist", "bio": "Civic tech tinkerer. Builds small dashboards from transit and city data.",
     "skills": ["python", "data visualization"], "interests": ["open data", "civic tech"], "wanted_skills": ["javascript"],
     "intent_kind": "looking_for_teammates", "intent_text": "Looking for a frontend developer for Transit Pulse.",
     "timezone": "Europe/Stockholm", "commitment": "5 hours weekly"},
    {"username": "omar_h", "display_name": "Omar Haddad", "bio": "Game developer. Tiny physics games and too many prototypes.",
     "skills": ["python", "gamedev"], "interests": ["games", "physics"], "wanted_skills": ["illustration"],
     "intent_kind": "open_to_collaboration", "intent_text": "Happy to trade code reviews on small games.",
     "timezone": "Europe/Berlin", "commitment": "3 hours weekly"},
    {"username": "alex_m", "display_name": "Alex Moreau", "bio": "Accessibility engineer. Forms, focus states and keyboard paths.",
     "skills": ["javascript", "accessibility"], "interests": ["education", "accessibility"], "wanted_skills": ["illustration"],
     "intent_kind": "looking_for_project", "intent_text": "Looking for an accessibility-focused project to contribute to.",
     "timezone": "Europe/Paris", "commitment": "4 hours weekly"},
    {"username": "priya_n", "display_name": "Priya Nair", "bio": "Data analyst who likes maps and simple charts.",
     "skills": ["python", "data visualization"], "interests": ["maps", "education"], "wanted_skills": ["javascript"],
     "intent_kind": "looking_for_project", "intent_text": "Looking for a civic data project with a map.",
     "timezone": "Asia/Kolkata", "commitment": "5 hours weekly"},
    {"username": "elena_v", "display_name": "Elena Voss", "bio": "Pixel artist and educator. Sketches for kids and game jams.",
     "skills": ["illustration", "design"], "interests": ["education", "kids"], "wanted_skills": ["javascript"],
     "intent_kind": "interested_in_event", "intent_text": "Joining the Spring Game Jam as an artist.",
     "timezone": "Europe/Helsinki", "commitment": "2 hours weekly"},
    {"username": "kenji_t", "display_name": "Kenji Tanaka", "bio": "Audio engineer. Helps small projects sound good.",
     "skills": ["python", "audio"], "interests": ["music", "open source"], "wanted_skills": ["design"],
     "intent_kind": "open_to_collaboration", "intent_text": "Open to audio work on open source projects.",
     "timezone": "Asia/Tokyo", "commitment": "3 hours weekly"},
]

PROJECTS = [
    {"owner": "sofia_l", "slug": "transit-pulse", "title": "Transit Pulse",
     "summary": "Live dashboard of city bus delays built on open data.",
     "description": "We ship small milestones every two weeks and share progress openly.",
     "tags": ["open data", "maps", "civic tech"], "skills": ["python", "data visualization", "javascript"],
     "stage": "building", "recruitment_status": "open", "commitment": "5 hours weekly",
     "experience_level": "any", "format": "online", "cover": ("bars", "blue"),
     "openings": [{"title": "Frontend developer", "role": "Frontend developer", "skills": ["javascript"],
                   "commitment": "5 hours weekly", "description": "Map view and delay filters in plain JavaScript."}],
     "applications": [("Frontend developer", "alex_m", "accepted", "I build accessible map UIs and can own the filters."),
                      ("Frontend developer", "priya_n", "accepted", "I have built two transit dashboards with open feeds."),
                      ("Frontend developer", "elena_v", None, "Happy to help with the visual language.")],
     "updates": [("Week 2: data loader", "The loader pulls two weeks of arrival data and caches it daily. Next: the first delay chart."),
                 ("Milestone 1: live map prototype", "The map shows delayed vehicles on three lines. Feedback welcome.")],
     "interested": ["elena_v", "kenji_t", "omar_h"], "saved": ["alex_m"]},
    {"owner": "alex_m", "slug": "pixel-board", "title": "Pixel Board",
     "summary": "Shared canvas for teaching kids basic programming.",
     "description": "A shared pixel canvas where kids change colours with a few lines of code.",
     "tags": ["education", "kids"], "skills": ["javascript", "illustration"],
     "stage": "prototype", "recruitment_status": "open", "format": "online", "cover": ("grid", "red"),
     "openings": [{"title": "Illustrator", "role": "Illustrator", "skills": ["illustration"],
                   "description": "Sprites and a small colour palette for beginners."}],
     "applications": [("Illustrator", "elena_v", None, "I draw pixel sprites for kids and would love to help.")],
     "updates": [], "interested": ["priya_n", "elena_v"], "saved": []},
    {"owner": "sofia_l", "slug": "study-graph", "title": "Study Graph",
     "summary": "Map of course prerequisites that helps students plan a semester.",
     "description": "Students see which courses unlock which, and plan a term without guesswork.",
     "tags": ["education", "planning"], "skills": ["python", "data visualization"],
     "stage": "idea", "recruitment_status": "open", "format": "online", "cover": ("constellation", "teal"),
     "openings": [{"title": "Backend developer", "role": "Backend developer", "skills": ["python"],
                   "description": "Import course catalogues and expose a prerequisite graph API."}],
     "applications": [("Backend developer", "priya_n", None, "I can prototype the import pipeline.")],
     "updates": [], "interested": ["priya_n"], "saved": []},
    {"owner": "omar_h", "slug": "orbit-runner", "title": "Orbit Runner",
     "summary": "Tiny physics game about slingshotting between planets.",
     "description": "One-button game about slingshotting between planets. Built in small prototypes.",
     "tags": ["games", "physics"], "skills": ["python", "gamedev"],
     "stage": "prototype", "recruitment_status": "unknown", "format": "online", "cover": ("orbit", "amber"),
     "openings": [], "applications": [], "updates": [],
     "interested": ["sofia_l", "kenji_t"], "saved": []},
    {"owner": "alex_m", "slug": "plain-forms", "title": "Plain Forms",
     "summary": "Accessible form components that work with a keyboard and screen reader.",
     "description": "Form components with visible errors, clear labels and full keyboard support.",
     "tags": ["accessibility", "ui"], "skills": ["javascript", "accessibility"],
     "stage": "building", "recruitment_status": "unknown", "format": "online", "cover": ("gradient", "violet"),
     "openings": [], "applications": [], "updates": [],
     "interested": ["omar_h"], "saved": []},
]

TEAMS = [
    {"owner": "kenji_t", "slug": "sound-lab", "title": "Sound Lab",
     "summary": "Audio engineers helping small projects sound great.",
     "description": "We record, mix and master audio for small open source projects.",
     "skills": ["python", "audio"], "topics": ["open source", "design"], "format": "online",
     "status": "recruiting", "cover": ("waves", "purple"),
     "openings": [{"title": "Sound designer", "role": "Sound designer", "skills": ["audio"],
                   "description": "Sound effects and short music loops for two games."}]},
    {"owner": "priya_n", "slug": "jam-squad", "title": "Jam Squad",
     "summary": "Teams that form during the Spring Game Jam and ship a small game together.",
     "description": "Jam Squad forms on the spot during the jam. Bring one skill and one idea.",
     "skills": ["python", "gamedev"], "topics": ["game jam"], "format": "online",
     "status": "recruiting", "event": "spring-game-jam", "cover": ("grid", "amber"),
     "openings": [{"title": "Gameplay programmer", "role": "Gameplay programmer", "skills": ["python"],
                   "description": "Core loop and controls for a ten-day jam game."}]},
]

COMMUNITIES = [
    {"owner": "elena_v", "slug": "open-source-starters", "title": "Open Source Starters",
     "summary": "First contributions, friendly reviews and good first issues.",
     "topics": ["open source", "mentoring"], "cover": ("constellation", "blue"),
     "members": ["sofia_l", "omar_h", "priya_n", "kenji_t"],
     "post": ("Good first issues this week",
              "Collected five small issues across our projects. Each has a short description and a mentor.")},
    {"owner": "omar_h", "slug": "indie-devs", "title": "Indie Devs",
     "summary": "Share progress on small games and get feedback.",
     "topics": ["games", "feedback"], "cover": ("orbit", "coral"),
     "members": ["alex_m", "elena_v", "kenji_t"],
     "post": ("Orbit Runner playtest round",
              "Looking for three testers to try the new orbit physics. Feedback in the comments, please.")},
]

EVENTS = [
    {"owner": "omar_h", "slug": "spring-game-jam", "title": "Spring Game Jam", "type": "game_jam",
     "summary": "Ten days, one theme, small games.",
     "description": "Ten days, one theme, small games. Teams form on the spot; mentors are around all event.",
     "start": at(-2), "end": at(8), "status": "active", "format": "online", "origin": "external",
     "source_name": "Jam Collective", "source_url": "https://example.org/jam-collective/spring-game-jam",
     "cover": ("grid", "violet"), "interested": ["sofia_l", "alex_m", "priya_n", "kenji_t", "elena_v"]},
    {"owner": "sofia_l", "slug": "open-data-weekend", "title": "Open Data Weekend", "type": "hackathon",
     "summary": "Two days with public datasets, maps and charts.",
     "description": "Bring a dataset, a laptop and a question about your city.",
     "start": at(3), "end": at(5), "format": "online",
     "cover": ("bars", "teal"), "interested": ["omar_h", "elena_v"]},
    {"owner": "alex_m", "slug": "accessibility-meetup", "title": "Accessibility Meetup", "type": "meetup",
     "summary": "Evening talks and live audits of small web apps.",
     "description": "Short talks on keyboard paths, focus and screen readers, then open audits.",
     "start": at(6, 18), "end": at(6, 20), "format": "local", "location": "City library, room 2",
     "cover": ("gradient", "blue"), "interested": ["sofia_l", "priya_n"]},
    {"owner": "kenji_t", "slug": "music-hack-day", "title": "Music Hack Day", "type": "hackathon",
     "summary": "One day of music tools, samples and small instruments.",
     "description": "Build a music toy, a sampler or a mixing helper in one day.",
     "start": at(13), "end": at(15), "format": "online",
     "cover": ("waves", "coral"), "interested": ["elena_v"]},
]

STORIES = [
    {"author": "sofia_l", "title": "Mapping prerequisites",
     "content": "Sketched the first prerequisite graph for Study Graph. Linear algebra turns out to be the busiest node.",
     "image": ("constellation", "teal"), "likes": ["omar_h", "alex_m", "kenji_t"],
     "comments": [("priya_n", "Linear algebra as the busiest node tracks with my experience.")]},
    {"author": "omar_h", "title": "Gravity tuning",
     "content": "Spent the evening tuning orbits in Orbit Runner. Small planets, big slingshots, lots of crashes.",
     "image": ("orbit", "amber"), "likes": ["sofia_l", "elena_v"],
     "comments": [("alex_m", "The crashes are the fun part. Keep them.")]},
    {"author": "alex_m", "title": "Keyboard-first forms",
     "content": "Plain Forms passes the full keyboard and screen-reader checklist now. Next: better error summaries.",
     "image": ("gradient", "violet"), "likes": ["sofia_l", "priya_n", "omar_h"],
     "comments": [("elena_v", "Error summaries are next on my list too."),
                  ("kenji_t", "Good to see this checklist in one place.")]},
    {"author": "priya_n", "title": "Bus delay histogram",
     "content": "Built a histogram of waiting times for Transit Pulse. Most delays cluster at rush hour, which is no surprise but looks good.",
     "image": ("bars", "blue"), "likes": ["sofia_l", "kenji_t", "elena_v"],
     "comments": [("sofia_l", "Let's put it on the dashboard next sprint.")]},
    {"author": "elena_v", "title": "Sketches for kids",
     "content": "Drew twelve pixel sprites for Pixel Board this weekend. The hardest one was a bicycle.",
     "image": None, "likes": ["alex_m", "priya_n"],
     "comments": [("alex_m", "A bicycle in twelve pixels is hard.")]},
    {"author": "kenji_t", "title": None,
     "content": "Mixed the first Sound Lab demo track from two stems and one bad cable. Recording notes are in the team room.",
     "image": ("waves", "purple"), "likes": ["omar_h", "priya_n", "sofia_l"],
     "comments": [("elena_v", "Share the stems when you can.")]},
]

FOLLOWS = [("priya_n", "sofia_l"), ("elena_v", "sofia_l"), ("kenji_t", "omar_h"),
           ("alex_m", "omar_h"), ("sofia_l", "omar_h"), ("omar_h", "alex_m")]


def ensure_empty():
    """Abort before any write if public listings already hold content."""
    for path in ("/discovery", "/explore", "/events", "/teams", "/communities", "/team-openings", "/people"):
        items = call("GET", path)["items"]
        if items:
            raise SystemExit(f"Refusing to seed: {path} already has {len(items)} item(s)")


def main():
    ensure_empty()
    ids, tokens = {}, {}
    for user in USERS:
        name = user["username"]
        ids[name] = call("POST", "/users", body={"username": name, "password": PASSWORD})["id"]
        tokens[name] = call("POST", "/login", body={"username": name, "password": PASSWORD})["access_token"]
        t = tokens[name]
        call("PATCH", "/me/profile", token=t, body={"display_name": user["display_name"], "bio": user["bio"]})
        style, color = AVATARS[len(ids) - 1]
        call("PUT", "/me/avatar", token=t, raw=picture(style, color, (512, 512), name))
        profile = {k: user[k] for k in ("skills", "interests", "wanted_skills", "intent_kind", "intent_text",
                                        "timezone", "commitment")}
        call("PUT", "/me/collaboration-profile", token=t,
             body={**profile, "discoverable": True, "status": "active", "languages": ["en"], "external_links": []})

    project_ids, opening_ids = {}, {}
    for project in PROJECTS:
        owner = tokens[project["owner"]]
        body = {k: project[k] for k in ("slug", "title", "summary", "description", "stage", "recruitment_status",
                                        "format", "tags", "skills") if k in project}
        body.update({"visibility": "public", "status": "active"})
        for key in ("commitment", "experience_level"):
            if key in project:
                body[key] = project[key]
        pid = call("POST", "/projects", token=owner, body=body)["id"]
        project_ids[project["slug"]] = pid
        slug = project["slug"]
        call("PUT", f"/projects/{slug}/cover", token=owner, raw=picture(*project["cover"], (1600, 900), slug))
        for opening in project["openings"]:
            opening_ids[(slug, opening["title"])] = call("POST", f"/projects/{slug}/openings", token=owner,
                                                         body=opening)["id"]
        for role, name, decision, message in project["applications"]:
            app_id = call("POST", f"/projects/{slug}/openings/{opening_ids[(slug, role)]}/applications",
                          token=tokens[name], body={"message": message})["id"]
            if decision:
                call("PATCH", f"/projects/{slug}/applications/{app_id}", token=owner, body={"status": decision})
        for title, content in project["updates"]:
            call("POST", "/posts", token=owner, body={"project_id": pid, "title": title, "content": content,
                                                      "is_published": True})
        for name in project["interested"]:
            call("PATCH", f"/projects/{slug}/engagement", token=tokens[name],
                 body={"interested": True, "interested_visible": True})
        for name in project["saved"]:
            call("PATCH", f"/projects/{slug}/engagement", token=tokens[name], body={"saved": True})

    event_ids = {}
    for event in EVENTS:
        owner = tokens[event["owner"]]
        body = {"slug": event["slug"], "title": event["title"], "summary": event["summary"],
                "description": event["description"], "type": event["type"], "starts_at": event["start"],
                "ends_at": event["end"], "timezone": "UTC", "format": event["format"],
                "visibility": "public", "status": event.get("status", "scheduled"),
                "participation_url": f"https://example.org/events/{event['slug']}"}
        for key in ("origin", "source_name", "source_url", "location"):
            if key in event:
                body[key] = event[key]
        created = call("POST", "/events", token=owner, body=body)
        event_ids[event["slug"]] = created["id"]
        call("PUT", f"/events/{event['slug']}/cover", token=owner, raw=picture(*event["cover"], (1600, 900), event["slug"]))
        for name in event["interested"]:
            call("PATCH", f"/events/{event['slug']}/engagement", token=tokens[name],
                 body={"interested": True, "interested_visible": True})

    team_ids = {}
    for team in TEAMS:
        owner = tokens[team["owner"]]
        body = {"slug": team["slug"], "title": team["title"], "summary": team["summary"],
                "description": team["description"], "skills": team["skills"], "topics": team["topics"],
                "format": "online", "visibility": "public", "status": team["status"]}
        if "event" in team:
            body["event_id"] = event_ids[team["event"]]
        team_ids[team["slug"]] = call("POST", "/teams", token=owner, body=body)["id"]
        call("PUT", f"/teams/{team['slug']}/cover", token=owner, raw=picture(*team["cover"], (1600, 900), team["slug"]))
        for opening in team["openings"]:
            call("POST", f"/teams/{team['slug']}/openings", token=owner, body={**opening, "status": "open"})

    community_ids = {}
    for community in COMMUNITIES:
        owner = tokens[community["owner"]]
        body = {"slug": community["slug"], "title": community["title"], "summary": community["summary"],
                "description": community["summary"], "topics": community["topics"], "format": "online",
                "visibility": "public"}
        community_ids[community["slug"]] = call("POST", "/communities", token=owner, body=body)["id"]
        slug = community["slug"]
        call("PUT", f"/communities/{slug}/cover", token=owner, raw=picture(*community["cover"], (1600, 900), slug))
        for name in community["members"]:
            call("PUT", f"/communities/{slug}/membership", token=tokens[name])
        title, content = community["post"]
        call("POST", "/posts", token=owner, body={"community_id": community_ids[slug], "title": title,
                                                  "content": content, "is_published": True})

    post_ids = {}
    for story in STORIES:
        author = tokens[story["author"]]
        body = {"content": story["content"], "is_published": True}
        if story["title"]:
            body["title"] = story["title"]
        post_id = call("POST", "/posts", token=author, body=body)["id"]
        post_ids[story["author"]] = post_id
        if story["image"]:
            style, color = story["image"]
            call("PUT", f"/posts/{post_id}/image", token=author, raw=picture(style, color, (1600, 900), story["author"]))
        for name in story["likes"]:
            call("PUT", f"/posts/{post_id}/likes", token=tokens[name])
        for name, text in story["comments"]:
            call("POST", f"/posts/{post_id}/comments", token=tokens[name], body={"content": text})
    for reader, author in FOLLOWS:
        call("POST", "/subscriptions", token=tokens[reader], body={"author_id": ids[author]})

    print(f"users: {len(ids)} ({', '.join(ids)})")
    print(f"projects: {len(project_ids)} ({', '.join(project_ids)})")
    print(f"teams: {len(team_ids)} ({', '.join(team_ids)})")
    print(f"communities: {len(community_ids)} ({', '.join(community_ids)})")
    print(f"events: {len(event_ids)} ({', '.join(event_ids)})")
    print(f"posts: {len(STORIES) + len(COMMUNITIES) + sum(len(p['updates']) for p in PROJECTS)} "
          f"(stories {len(post_ids)}, project updates {sum(len(p['updates']) for p in PROJECTS)}, "
          f"community {len(COMMUNITIES)})")
    print(f"follows: {len(FOLLOWS)}")


if __name__ == "__main__":
    BASE = sys.argv[1].rstrip("/") if len(sys.argv) == 2 else ""
    if not BASE:
        raise SystemExit("Usage: python seed_readme_preview.py BASE_URL")
    # Public listings cannot reveal private accounts, so the container's own URL decides.
    if os.environ.get("PUBLIC_APP_URL", "").rstrip("/") != PREVIEW_URL:
        raise SystemExit(f"Refusing to seed: PUBLIC_APP_URL is not the isolated preview {PREVIEW_URL}")
    main()
