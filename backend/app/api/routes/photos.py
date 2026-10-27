"""Фото профиля: загрузка, удаление, порядок и отдача по подписанной ссылке."""

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select

from app.api.deps import CurrentUser, PhotoUrl, SessionDep
from app.api.photo_links import verify_photo_link
from app.api.routes.me import load_me
from app.api.schemas import MeOut, PhotoOrderIn
from app.db.models import UserPhoto
from app.domain.time import utcnow
from app.services.photos import MAX_UPLOAD_BYTES, PhotoError, process_photo

MAX_PHOTOS = 3

router = APIRouter(tags=["фото"])


async def _my_photos(session, user_id: int) -> list[UserPhoto]:
    return list(
        await session.scalars(
            select(UserPhoto).where(UserPhoto.user_id == user_id).order_by(UserPhoto.position, UserPhoto.id)
        )
    )


@router.post("/me/photos", response_model=MeOut)
async def upload_photo(file: UploadFile, user: CurrentUser, session: SessionDep, photo_url: PhotoUrl) -> MeOut:
    """Добавить фото в конец (первое — главное). До трёх фото, файл до 10 МБ: JPEG, PNG или WebP."""
    count = await session.scalar(select(func.count(UserPhoto.id)).where(UserPhoto.user_id == user.id))
    if count >= MAX_PHOTOS:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="too_many_photos")

    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        # Пережатие занимает процессор — не держим им цикл событий
        data, width, height = await run_in_threadpool(process_photo, raw)
    except PhotoError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.code) from None

    last_position = await session.scalar(select(func.max(UserPhoto.position)).where(UserPhoto.user_id == user.id))
    position = 0 if last_position is None else last_position + 1
    session.add(UserPhoto(user_id=user.id, position=position, data=data, width=width, height=height))
    await session.commit()
    return await load_me(session, user.id, photo_url)


@router.delete("/me/photos/{photo_id}", response_model=MeOut)
async def delete_photo(photo_id: int, user: CurrentUser, session: SessionDep, photo_url: PhotoUrl) -> MeOut:
    photos = await _my_photos(session, user.id)
    photo = next((photo for photo in photos if photo.id == photo_id), None)
    if photo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="photo_not_found")
    await session.delete(photo)
    for position, rest in enumerate(item for item in photos if item.id != photo_id):
        rest.position = position
    await session.commit()
    return await load_me(session, user.id, photo_url)


@router.put("/me/photos/order", response_model=MeOut)
async def reorder_photos(body: PhotoOrderIn, user: CurrentUser, session: SessionDep, photo_url: PhotoUrl) -> MeOut:
    """Задать порядок своих фото целиком — так фото делается главным."""
    photos = {photo.id: photo for photo in await _my_photos(session, user.id)}
    if sorted(body.photo_ids) != sorted(photos):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="photo_order_mismatch")
    for position, photo_id in enumerate(body.photo_ids):
        photos[photo_id].position = position
    await session.commit()
    return await load_me(session, user.id, photo_url)


@router.get("/photos/{photo_id}", include_in_schema=False)
async def get_photo(photo_id: int, e: int, s: str, request: Request, session: SessionDep) -> Response:
    """Отдаёт фото по подписанной ссылке. Право смотреть проверяется, когда API выдаёт ссылку."""
    now = utcnow()
    if not verify_photo_link(photo_id, e, s, request.app.state.photo_secret, now):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    data = await session.scalar(select(UserPhoto.data).where(UserPhoto.id == photo_id))
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # private — кэшировать можно только в браузере смотрящего, не в общих прокси
    max_age = max(int(e - now.timestamp()), 0)
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": f"private, max-age={max_age}"})
