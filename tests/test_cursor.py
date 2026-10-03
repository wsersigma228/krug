import base64
import hmac
import json
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.config import SECRET_KEY
from backend.pagination import decode_cursor, encode_cursor


def sign_payload(payload):
    data = json.dumps(payload).encode()
    signature = hmac.digest(SECRET_KEY.encode(), b"pagination-v1:" + data, "sha256")
    return ".".join(base64.urlsafe_b64encode(part).rstrip(b"=").decode() for part in (data, signature))


@pytest.mark.parametrize("changes", [
    {"id": 0}, {"id": -1}, {"id": 2147483648}, {"id": True}, {"id": 1.5}, {"id": "1"},
    {"created_at": "2026-01-01T00:00:00"}, {"created_at": "not-a-date"},
    {"created_at": None}, {"version": 2}, {"unexpected": "field"},
])
def test_invalid_signed_payload_is_rejected(changes):
    # Validate the payload even when its signature is valid.
    token = sign_payload({
        "version": 1, "created_at": "2026-01-01T00:00:00Z", "id": 1, "scope": "test", **changes,
    })
    with pytest.raises(HTTPException) as error:
        decode_cursor(token, "test")
    assert error.value.status_code == 422


@pytest.mark.parametrize("token", ["💩.abc", "a.b.c", "@@@.@@@", ".", "a.a", "eyJhIjoxfQ=."])
def test_malformed_encoding_is_rejected(token):
    with pytest.raises(HTTPException) as error:
        decode_cursor(token, "test")
    assert error.value.status_code == 422


def test_cursor_preserves_microseconds():
    timestamp = datetime(2026, 1, 1, 12, 30, 45, 123456, tzinfo=timezone.utc)
    cursor = decode_cursor(encode_cursor(timestamp, 42, "test"), "test")
    assert cursor.created_at == timestamp
    assert cursor.id == 42


@pytest.mark.parametrize("rank", [-1.0, float("inf"), float("nan"), "0.5", True])
def test_invalid_search_rank_is_rejected(rank):
    token = sign_payload({
        "version": 1, "created_at": "2026-01-01T00:00:00Z", "id": 1,
        "scope": "search", "rank": rank,
    })
    with pytest.raises(HTTPException):
        decode_cursor(token, "search", ranked=True)


def test_search_cursor_round_trip_and_mode():
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rank = 0.6079270839691162
    token = encode_cursor(timestamp, 42, "search", rank=rank)
    assert decode_cursor(token, "search", ranked=True).rank == rank
    with pytest.raises(HTTPException):
        decode_cursor(token, "search")
    with pytest.raises(HTTPException):
        decode_cursor(encode_cursor(timestamp, 42, "search"), "search", ranked=True)
