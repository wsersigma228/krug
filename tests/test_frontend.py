import pytest

pytestmark = pytest.mark.asyncio


async def test_frontend_and_token_pages_have_external_assets_and_csp(client):
    for path in ("/app", "/verify-email", "/reset-password"):
        response = await client.get(path)
        assert response.status_code == 200
        assert '/assets/app.js' in response.text
        assert 'unsafe-inline' not in response.headers['content-security-policy']
        assert response.headers['cache-control'] == 'no-store'
    assert (await client.get('/assets/app.js')).status_code == 200
    assert (await client.get('/assets/style.css')).status_code == 200


async def test_readiness_returns_503_without_connection_details(client, monkeypatch):
    class OfflineRedis:
        async def __aenter__(self):
            raise OSError('private connection details')
        async def __aexit__(self, *args):
            pass
    monkeypatch.setattr('backend.main.Redis.from_url', lambda *args, **kwargs: OfflineRedis())
    response = await client.get('/health')
    assert response.status_code == 503
    assert response.json() == {'detail': 'Dependency unavailable'}


async def test_explore_only_published_posts_search_and_cursor(client, accounts):
    author, reader = accounts
    ids = []
    for user, title, published in ((author, "Running story", True), (reader, "Runs daily", True),
                                   (author, "Running private", False)):
        response = await client.post('/posts', headers=user['headers'], json={
            'title': title, 'content': 'Body', 'is_published': published})
        assert response.status_code == 201
        ids.append(response.json()['id'])
    page = (await client.get('/explore', params={'search': 'run', 'search_language': 'english', 'limit': 1})).json()
    assert page['has_more']
    second = (await client.get('/explore', params={
        'search': 'run', 'search_language': 'english', 'limit': 1, 'cursor': page['next_cursor']})).json()
    items = page['items'] + second['items']
    assert {p['id'] for p in items} == set(ids[:2])
    assert {p['author_username'] for p in items} == {author['username'], reader['username']}
    assert all('email' not in p for p in items)
    assert not second['has_more']
    assert (await client.get('/explore', params={'cursor': page['next_cursor']})).status_code == 422
    assert (await client.get('/explore?is_published=false')).status_code == 422
    assert (await client.get('/explore?search=private')).json()['items'] == []
