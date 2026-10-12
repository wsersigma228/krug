from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import PUBLIC_APP_URL
from backend.database import get_db
from backend.models import Community, Event, Team
from backend.routes.communities import community_responses
from backend.routes.platform_common import visible
from backend.routes.teams import team_responses


router = APIRouter()


@router.get("/team/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def team_page(slug: str, db: AsyncSession = Depends(get_db)):
    team = await visible(db, Team, slug)
    card = (await team_responses(db, [team]))[0]
    return public_page(team.title, team.summary, "team", slug,
        f'<p>{escape(team.summary)}</p><div class="prose">{escape(team.description)}</div>'
        f'<p>{card.member_count} members · {card.openings_count} open roles</p>', team.cover_url)


@router.get("/community/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def community_page(slug: str, db: AsyncSession = Depends(get_db)):
    community = await visible(db, Community, slug)
    card = (await community_responses(db, [community]))[0]
    return public_page(community.title, community.summary, "community", slug,
        f'<p>{escape(community.summary)}</p><div class="prose">{escape(community.description)}</div>'
        f'<p>{card.member_count} members · {card.published_posts_count} posts</p>', community.cover_url)


@router.get("/event/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def event_page(slug: str, db: AsyncSession = Depends(get_db)):
    event = await visible(db, Event, slug)
    return public_page(event.title, event.summary, "event", slug,
        f'<p>{escape(event.summary)}</p><div class="prose">{escape(event.description)}</div>'
        f'<p>{escape(event.starts_at.isoformat())} · {escape(event.timezone)}</p>', event.cover_url)


def public_page(title, description, kind, slug, body, image_url=None):
    safe_title, safe_description = escape(title), escape(description)
    app_url = escape(PUBLIC_APP_URL, quote=True)
    image = f'<meta property="og:image" content="{escape(PUBLIC_APP_URL + image_url, quote=True)}">' if image_url else ""
    cover = f'<img class="cover" src="{escape(image_url, quote=True)}" alt="">' if image_url else ""
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{safe_title} · Krug</title>
<meta name="description" content="{safe_description}"><meta property="og:title" content="{safe_title}">
<meta property="og:description" content="{safe_description}"><meta property="og:type" content="website">
<meta property="og:url" content="{app_url}/{kind}/{escape(slug, quote=True)}">
{image}<style>body{{margin:0;background:#10151c;color:#e8edf5;font:16px/1.65 system-ui,sans-serif}}header,main{{max-width:900px;margin:auto;padding:24px}}a{{color:#9ecbff}}main{{margin-top:8vh}}h1{{font-size:clamp(2rem,6vw,4rem);line-height:1.1}}.prose{{white-space:pre-wrap}}.summary{{color:#b5c2d2}}.cover{{display:block;max-width:100%;max-height:480px;object-fit:cover;border-radius:12px}}</style></head>
<body><header><a href="{app_url}/app">Krug</a></header><main>{cover}<h1>{safe_title}</h1>
<p class="summary">{safe_description}</p>{body}<p><a href="{app_url}/app#/{kind}/{escape(slug, quote=True)}">Open in Krug</a></p>
</main></body></html>''', headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
