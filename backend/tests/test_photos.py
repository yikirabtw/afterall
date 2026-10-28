"""Фото профиля: пережатие без EXIF, лимит в 3 фото, порядок, подписанные ссылки."""

import io
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from initdata import auth
from PIL import Image

from app.api.photo_links import make_photo_url, verify_photo_link

ORIENTATION_TAG = 0x0112
DESCRIPTION_TAG = 0x010E
GPS_IFD_TAG = 0x8825


def make_jpeg(width: int = 2000, height: int = 1000, *, orientation: int | None = None, with_gps: bool = True) -> bytes:
    exif = Image.Exif()
    exif[DESCRIPTION_TAG] = "secret-note"
    if orientation:
        exif[ORIENTATION_TAG] = orientation
    if with_gps:
        exif.get_ifd(GPS_IFD_TAG).update({1: "N", 2: (55.0, 45.0, 21.0)})  # широта Москвы
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "teal").save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


async def upload(client, data: bytes, filename: str = "photo.jpg", content_type: str = "image/jpeg"):
    return await client.post("/api/me/photos", files={"file": (filename, data, content_type)}, headers=auth())


async def test_upload_strips_exif_and_resizes(client):
    response = await upload(client, make_jpeg())

    assert response.status_code == 200, response.text
    [photo] = response.json()["photos"]
    image_response = await client.get(photo["url"])
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/jpeg"
    assert "private" in image_response.headers["cache-control"]

    image = Image.open(io.BytesIO(image_response.content))
    assert max(image.size) == 1280
    assert len(image.getexif()) == 0  # ни GPS, ни подписи — EXIF вырезан целиком


async def test_upload_applies_exif_orientation(client):
    # Снимок «лёжа» с пометкой «повернуть на 90°» — после обработки должен стать вертикальным
    response = await upload(client, make_jpeg(2000, 1000, orientation=6, with_gps=False))

    [photo] = response.json()["photos"]
    image = Image.open(io.BytesIO((await client.get(photo["url"])).content))
    width, height = image.size
    assert height > width
    # Клиент получает размеры уже повёрнутого снимка — по ним шапка профиля подстраивает высоту
    assert (photo["width"], photo["height"]) == (width, height)


@pytest.mark.parametrize(
    ("kind", "code"),
    [("not_an_image", "photo_unreadable"), ("too_large", "photo_too_large")],
)
async def test_bad_files_are_rejected(client, kind, code):
    # Файл создаётся внутри теста: 10 МБ в параметрах раздули бы вывод pytest
    data = b"definitely not an image" if kind == "not_an_image" else b"x" * (10 * 1024 * 1024 + 1)
    response = await upload(client, data)
    assert response.status_code == 422
    assert response.json()["detail"] == code


async def test_gif_is_not_supported(client):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, "GIF")
    response = await upload(client, buffer.getvalue(), "a.gif", "image/gif")
    assert response.json()["detail"] == "photo_format_not_supported"


async def test_at_most_three_photos(client):
    for _ in range(3):
        assert (await upload(client, make_jpeg(400, 400))).status_code == 200

    response = await upload(client, make_jpeg(400, 400))

    assert response.status_code == 409
    assert response.json()["detail"] == "too_many_photos"


async def test_reorder_and_delete(client):
    for _ in range(3):
        photos = (await upload(client, make_jpeg(400, 400))).json()["photos"]
    first, second, third = (photo["id"] for photo in photos)

    reordered = await client.put("/api/me/photos/order", json={"photo_ids": [third, first, second]}, headers=auth())
    assert [photo["id"] for photo in reordered.json()["photos"]] == [third, first, second]

    after_delete = await client.delete(f"/api/me/photos/{third}", headers=auth())
    assert [photo["id"] for photo in after_delete.json()["photos"]] == [first, second]

    wrong = await client.put("/api/me/photos/order", json={"photo_ids": [first]}, headers=auth())
    assert wrong.json()["detail"] == "photo_order_mismatch"


async def test_cannot_touch_someone_elses_photo(client, make_player):
    other = await make_player()
    photo_id = (await client.post(
        "/api/me/photos", files={"file": ("a.jpg", make_jpeg(400, 400), "image/jpeg")}, headers=other.headers
    )).json()["photos"][0]["id"]

    response = await client.delete(f"/api/me/photos/{photo_id}", headers=auth())

    assert response.status_code == 404


async def test_photo_link_must_be_signed(client):
    [photo] = (await upload(client, make_jpeg(400, 400))).json()["photos"]
    query = parse_qs(urlsplit(photo["url"]).query)
    path = urlsplit(photo["url"]).path

    tampered = await client.get(f"{path}?e={query['e'][0]}&s={'0' * 32}")
    other_photo = await client.get(f"/api/photos/{photo['id'] + 1}?e={query['e'][0]}&s={query['s'][0]}")

    assert tampered.status_code == 403
    assert other_photo.status_code == 403  # подпись привязана к id фото


def test_photo_link_expires():
    now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
    query = parse_qs(urlsplit(make_photo_url(7, "secret", now)).query)
    expires, signature = int(query["e"][0]), query["s"][0]

    assert verify_photo_link(7, expires, signature, "secret", now + timedelta(hours=5))
    assert not verify_photo_link(7, expires, signature, "secret", now + timedelta(hours=13))
    assert not verify_photo_link(7, expires, signature, "other-secret", now)


def test_same_link_within_window_for_browser_cache():
    now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
    assert make_photo_url(7, "secret", now) == make_photo_url(7, "secret", now + timedelta(minutes=30))


async def test_profile_limits(client):
    too_long_name = await client.put("/api/me/profile", json={"display_name": "x" * 21}, headers=auth())
    too_long_bio = await client.put("/api/me/profile", json={"display_name": "Аня", "bio": "x" * 151}, headers=auth())
    ok = await client.put("/api/me/profile", json={"display_name": "x" * 20, "bio": "x" * 150}, headers=auth())

    assert (too_long_name.status_code, too_long_bio.status_code, ok.status_code) == (422, 422, 200)
