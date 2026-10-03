import base64
import hashlib
import hmac
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import Select, tuple_

from backend.config import SECRET_KEY


class Cursor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1] = 1
    created_at: AwareDatetime
    id: int = Field(gt=0, le=2147483647)
    scope: str
    rank: float | None = Field(default=None, ge=0, allow_inf_nan=False)


def cursor_scope(endpoint: str, **filters) -> str:
    data = json.dumps([endpoint, filters], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def _base64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unbase64(value: str) -> bytes:
    decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    if _base64(decoded) != value:
        raise ValueError("Non-canonical cursor")
    return decoded


def encode_cursor(created_at: datetime, row_id: int, scope: str, rank: float | None = None) -> str:
    payload = Cursor(created_at=created_at.astimezone(timezone.utc), id=row_id, scope=scope, rank=rank)
    data = payload.model_dump_json().encode()
    signature = hmac.digest(SECRET_KEY.encode(), b"pagination-v1:" + data, "sha256")
    return f"{_base64(data)}.{_base64(signature)}"


def decode_cursor(token: str | None, scope: str, *, ranked: bool = False) -> Cursor | None:
    if token is None:
        return None
    try:
        if not 1 <= len(token) <= 2048:
            raise ValueError("Invalid cursor length")
        data_part, signature_part = token.split(".")
        data, signature = _unbase64(data_part), _unbase64(signature_part)
        expected = hmac.digest(SECRET_KEY.encode(), b"pagination-v1:" + data, "sha256")
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        cursor = Cursor.model_validate_json(data)
        # A cursor belongs to one endpoint, user and set of filters.
        if cursor.scope != scope or (cursor.rank is not None) != ranked:
            raise ValueError("Cursor scope changed")
        return cursor
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid cursor for this request") from None


def seek_page(query: Select, model, cursor: Cursor | None, limit: int) -> Select:
    if cursor is not None:
        query = query.where(
            tuple_(model.created_at, model.id) < tuple_(cursor.created_at, cursor.id)
        )
    # One extra row tells us whether another page exists.
    return query.order_by(model.created_at.desc(), model.id.desc()).limit(limit + 1)


def make_page(rows: Sequence, limit: int, scope: str) -> dict:
    items = list(rows[:limit])
    has_more = len(rows) > limit
    next_cursor = None
    if has_more:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, last.id, scope)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
