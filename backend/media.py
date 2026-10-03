"""Small local photo store. The database owns the current file reference."""
from io import BytesIO
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.config import MEDIA_ROOT

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000


def save_photo(data: bytes) -> str:
    try:
        with Image.open(BytesIO(data), formats=["JPEG", "PNG", "WEBP"]) as source:
            if source.width * source.height > MAX_PIXELS or getattr(source, "n_frames", 1) != 1:
                raise HTTPException(422, "Use a still image of at most 16 megapixels")
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2560, 2560))
            # Re-encoding removes metadata and any appended non-image payload.
            output = BytesIO()
            image.save(output, format="JPEG", quality=85)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Invalid JPEG, PNG or WebP image") from None
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    key = f"{uuid4().hex}.jpg"
    path = MEDIA_ROOT / key
    try:
        with path.open("xb") as file:
            file.write(output.getvalue())
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return key


def delete_photo(key: str | None):
    if key:
        (MEDIA_ROOT / key).unlink(missing_ok=True)
