from uuid import uuid4


def slug(prefix):
    return f"{prefix}-{uuid4().hex[:12]}"


async def make_team(client, headers, visibility="public", **changes):
    body = {"slug": slug("team"), "title": "Game team", "summary": "Looking for artists",
            "visibility": visibility, "skills": ["art"], "languages": ["en"]}
    body.update(changes)
    response = await client.post("/teams", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def make_opening(client, headers, team_slug, **changes):
    body = {"title": "Artist", "role": "2D artist", "skills": ["art"], "description": "Concepts"}
    body.update(changes)
    response = await client.post(f"/teams/{team_slug}/openings", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_team_openings_feed_filters_visibility_and_status(client, accounts):
    owner, _ = accounts
    tag = uuid4().hex[:10]
    skill = f"skill-{tag}"
    public = await make_team(client, owner["headers"])
    draft = await make_team(client, owner["headers"], visibility="draft")
    archived = await make_team(client, owner["headers"])
    assert (await client.patch(f"/teams/{archived['slug']}", headers=owner["headers"],
                               json={"status": "archived"})).status_code == 200

    open_role = await make_opening(client, owner["headers"], public["slug"], skills=[skill], title=f"Open {tag}")
    closed_role = await make_opening(client, owner["headers"], public["slug"], skills=[skill])
    assert (await client.patch(f"/team-openings/{closed_role['id']}", headers=owner["headers"],
                               json={"status": "closed"})).status_code == 200
    hidden_role = await make_opening(client, owner["headers"], draft["slug"], skills=[skill])
    archived_role = await make_opening(client, owner["headers"], archived["slug"], skills=[skill])
    active = await make_team(client, owner["headers"])
    active_role = await make_opening(client, owner["headers"], active["slug"], skills=[skill])
    assert (await client.patch(f"/teams/{active['slug']}", headers=owner["headers"],
                               json={"status": "active"})).status_code == 200

    # Anonymous readers see only open roles of public teams that are recruiting.
    items = (await client.get("/team-openings", params={"skill": skill})).json()["items"]
    assert [row["id"] for row in items] == [open_role["id"]]
    assert items[0]["team"] == {"slug": public["slug"], "title": public["title"], "summary": public["summary"]}
    assert items[0]["team_id"] == public["id"]
    ids = {row["id"] for row in (await client.get("/team-openings", params={"skill": skill})).json()["items"]}
    assert closed_role["id"] not in ids and hidden_role["id"] not in ids and archived_role["id"] not in ids
    assert active_role["id"] not in ids

    by_search = (await client.get("/team-openings", params={"search": tag.upper()})).json()["items"]
    assert [row["id"] for row in by_search] == [open_role["id"]]
    assert (await client.get("/team-openings", params={"search": f"nomatch-{tag}"})).json()["items"] == []


async def test_team_openings_feed_paginates_newest_first(client, accounts):
    owner, _ = accounts
    skill = f"page-{uuid4().hex[:10]}"
    team = await make_team(client, owner["headers"])
    created = [await make_opening(client, owner["headers"], team["slug"], skills=[skill]) for _ in range(3)]
    expected = [row["id"] for row in reversed(created)]

    first = (await client.get("/team-openings", params={"skill": skill, "limit": 2})).json()
    assert [row["id"] for row in first["items"]] == expected[:2]
    assert first["has_more"] is True and first["next_cursor"]
    second = (await client.get("/team-openings", params={"skill": skill, "limit": 2,
                                                         "cursor": first["next_cursor"]})).json()
    assert [row["id"] for row in second["items"]] == expected[2:]
    assert second["has_more"] is False and second["next_cursor"] is None

    # A cursor is bound to its filters.
    reused = await client.get("/team-openings", params={"search": "other", "cursor": first["next_cursor"]})
    assert reused.status_code == 422


async def test_team_openings_feed_rejects_invalid_limit(client):
    assert (await client.get("/team-openings", params={"limit": 0})).status_code == 422
