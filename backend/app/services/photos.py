"""Подготовка фото профиля перед сохранением."""

import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SIDE = 1280  # по большей стороне — хватает для полноэкранной анкеты на телефоне
JPEG_QUALITY = 82
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
# Защита от «бомб» — крошечных файлов, которые при распаковке занимают гигабайты
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class PhotoError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def process_photo(raw: bytes) -> tuple[bytes, int, int]:
    """Возвращает (jpeg, ширина, высота).

    Фото поворачивается по EXIF и сохраняется заново БЕЗ EXIF: в снимках с телефона там бывают
    GPS-координаты — то есть точный адрес, а мы обещаем не раскрывать геолокацию.
    """
    if len(raw) > MAX_UPLOAD_BYTES:
        raise PhotoError("photo_too_large")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ALLOWED_FORMATS:
                    raise PhotoError("photo_format_not_supported")
                image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((MAX_SIDE, MAX_SIDE))
        output = io.BytesIO()
        image.save(output, "JPEG", quality=JPEG_QUALITY, optimize=True)  # exif не передаём — его не будет
    except PhotoError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError):
        raise PhotoError("photo_unreadable") from None
    return output.getvalue(), image.width, image.height
