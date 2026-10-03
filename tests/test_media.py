from io import BytesIO

import pytest
from PIL import Image


def photo(fmt="PNG", size=(32, 24)):
    data = BytesIO()
    Image.new("RGB", size, "red").save(data, format=fmt)
    return data.getvalue()


@pytest.fixture(autouse=True)
def temporary_media(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.media.MEDIA_ROOT", tmp_path)
    monkeypatch.setattr("backend.routes.media.MEDIA_ROOT", tmp_path)
    return tmp_path


@pytest.mark.asyncio
async def test_photo_permissions_visibility_and_cleanup(client, accounts, temporary_media):
    author, reader = accounts
    post = (await client.post("/posts", headers=author["headers"], json={"title": "Photo", "content": "Body"})).json()
    url = f"/posts/{post['id']}/image"
    assert (await client.put(url, headers=reader["headers"], content=photo())).status_code == 404
    response = await client.put(url, headers=author["headers"], content=photo())
    assert response.status_code == 200, response.text
    assert response.json()["image_url"].startswith(url)
    assert len(list(temporary_media.iterdir())) == 1
    assert (await client.get(url)).status_code == 404
    assert (await client.get(url, headers=reader["headers"])).status_code == 404
    image = await client.get(url, headers=author["headers"])
    assert image.status_code == 200
    assert image.headers["cache-control"] == "no-store"
    with Image.open(BytesIO(image.content)) as decoded:
        assert decoded.format == "JPEG"
        assert decoded.size == (32, 24)
    await client.put(f"/posts/{post['id']}", headers=author["headers"], json={"is_published": True})
    assert (await client.get(url)).status_code == 200
    await client.put(url, headers=author["headers"], content=photo("WEBP"))
    assert len(list(temporary_media.iterdir())) == 1
    await client.put(f"/posts/{post['id']}", headers=author["headers"], json={"is_published": False})
    assert (await client.get(url)).status_code == 404
    assert (await client.delete(url, headers=reader["headers"])).status_code == 404
    assert (await client.delete(url, headers=author["headers"])).status_code == 204
    assert list(temporary_media.iterdir()) == []
    await client.put(url, headers=author["headers"], content=photo("JPEG"))
    assert (await client.delete(f"/posts/{post['id']}", headers=author["headers"])).status_code == 204
    assert list(temporary_media.iterdir()) == []


@pytest.mark.asyncio
async def test_reject_invalid_oversized_and_animated_photos(client, accounts, temporary_media, monkeypatch):
    author, _ = accounts
    post = (await client.post("/posts", headers=author["headers"], json={"title": "Photo", "content": "Body"})).json()
    url = f"/posts/{post['id']}/image"
    for data in (b"", b"<svg></svg>", photo()[:24], photo("GIF")):
        response = await client.put(url, headers=author["headers"], content=data)
        assert response.status_code == 422, response.text
    monkeypatch.setattr("backend.routes.media.MAX_UPLOAD_BYTES", 30)
    assert (await client.put(url, headers=author["headers"], content=photo())).status_code == 413
    monkeypatch.setattr("backend.routes.media.MAX_UPLOAD_BYTES", 8 * 1024 * 1024)
    monkeypatch.setattr("backend.media.MAX_PIXELS", 10)
    assert (await client.put(url, headers=author["headers"], content=photo())).status_code == 422
    monkeypatch.setattr("backend.media.MAX_PIXELS", 16_000_000)
    data = BytesIO()
    Image.new("RGB", (10, 10), "red").save(data, format="PNG", save_all=True,
        append_images=[Image.new("RGB", (10, 10), "blue")])
    assert (await client.put(url, headers=author["headers"], content=data.getvalue())).status_code == 422
    assert list(temporary_media.iterdir()) == []


@pytest.mark.asyncio
async def test_account_delete_removes_photos(client, accounts, temporary_media):
    author, _ = accounts
    post = (await client.post("/posts", headers=author["headers"], json={"title": "Photo", "content": "Body"})).json()
    await client.put(f"/posts/{post['id']}/image", headers=author["headers"], content=photo())
    assert len(list(temporary_media.iterdir())) == 1
    assert (await client.delete(f"/users/{author['id']}", headers=author["headers"])).status_code == 204
    assert list(temporary_media.iterdir()) == []


@pytest.mark.asyncio
async def test_missing_photo_returns_404(client, accounts, temporary_media):
    author, _ = accounts
    post = (await client.post("/posts", headers=author["headers"], json={
        "title": "Photo", "content": "Body", "is_published": True})).json()
    url = f"/posts/{post['id']}/image"
    await client.put(url, headers=author["headers"], content=photo())
    for path in temporary_media.iterdir():
        path.unlink()
    assert (await client.get(url)).status_code == 404


async def test_photo_orientation_applied_and_private_metadata_removed(client, accounts):
    author, _ = accounts
    post = (await client.post("/posts", headers=author["headers"], json={"content": "Photo"})).json()
    url = f"/posts/{post['id']}/image"
    source = Image.new("RGB", (40, 20), "red")
    source.paste("blue", (20, 0, 40, 20))
    exif = Image.Exif()
    exif[274] = 6  # Camera orientation: rotate 90 degrees clockwise.
    exif[315] = "private-camera-owner"
    data = BytesIO()
    source.save(data, format="JPEG", exif=exif)
    payload = b"appended-private-payload"
    uploaded = await client.put(url, headers=author["headers"], content=data.getvalue() + payload)
    assert uploaded.status_code == 200, uploaded.text
    response = await client.get(url, headers=author["headers"])
    assert response.status_code == 200, response.text
    assert payload not in response.content
    assert b"private-camera-owner" not in response.content
    assert response.content.endswith(b"\xff\xd9")
    with Image.open(BytesIO(response.content)) as decoded:
        assert decoded.size == (20, 40)
        assert not decoded.getexif()
        top, bottom = decoded.getpixel((10, 5)), decoded.getpixel((10, 35))
        assert top[0] > top[2] and bottom[2] > bottom[0]


async def test_large_allowed_photo_keeps_aspect_ratio_when_downsampled(client, accounts):
    author, _ = accounts
    post = (await client.post("/posts", headers=author["headers"], json={"content": "Large photo"})).json()
    url = f"/posts/{post['id']}/image"
    response = await client.put(url, headers=author["headers"], content=photo(size=(3200, 1600)))
    assert response.status_code == 200, response.text
    response = await client.get(url, headers=author["headers"])
    assert response.status_code == 200, response.text
    with Image.open(BytesIO(response.content)) as decoded:
        assert decoded.size == (2560, 1280)


async def test_rejected_replacements_keep_existing_photo(client, accounts, temporary_media, monkeypatch):
    author, _ = accounts
    headers = author["headers"]
    post = (await client.post("/posts", headers=headers, json={"content": "Photo"})).json()
    url = f"/posts/{post['id']}/image"
    uploaded = await client.put(url, headers=headers, content=photo())
    assert uploaded.status_code == 200, uploaded.text
    original_url = uploaded.json()["image_url"]
    original_file, = temporary_media.iterdir()
    original_bytes = original_file.read_bytes()
    for data, status in ((b"invalid-image", 422), (photo()[:24], 422), (photo(), 413)):
        if status == 413:
            monkeypatch.setattr("backend.routes.media.MAX_UPLOAD_BYTES", 30)
        response = await client.put(url, headers=headers, content=data)
        assert response.status_code == status, response.text
        assert (await client.get(f"/posts/{post['id']}", headers=headers)).json()["image_url"] == original_url
        assert list(temporary_media.iterdir()) == [original_file]
        assert original_file.read_bytes() == original_bytes
        assert (await client.get(url, headers=headers)).content == original_bytes


async def test_failed_photo_commit_removes_only_new_file(client, accounts, db, temporary_media, monkeypatch):
    author, _ = accounts
    headers = author["headers"]
    post = (await client.post("/posts", headers=headers, json={"content": "Photo"})).json()
    url = f"/posts/{post['id']}/image"
    uploaded = await client.put(url, headers=headers, content=photo())
    assert uploaded.status_code == 200, uploaded.text
    original_url = uploaded.json()["image_url"]
    original_file, = temporary_media.iterdir()
    original_bytes = original_file.read_bytes()

    async def fail_commit():
        raise RuntimeError("injected database commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="injected database commit failure"):
            await client.put(url, headers=headers, content=photo(size=(64, 48)))
    await db.rollback()
    assert list(temporary_media.iterdir()) == [original_file]
    assert original_file.read_bytes() == original_bytes
    assert (await client.get(f"/posts/{post['id']}", headers=headers)).json()["image_url"] == original_url
    assert (await client.get(url, headers=headers)).content == original_bytes
