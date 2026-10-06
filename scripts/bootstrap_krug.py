"""Operator-only fresh start. Back up DB and media before explicitly resetting data."""
import argparse
import asyncio
import json
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url

from backend.config import DATABASE_URL
from backend.database import Base, SessionLocal
from backend.models import User, Project
from backend.security import get_password_hash


async def bootstrap(expected_database: str, reset_data: bool, account: dict):
    if make_url(DATABASE_URL).database != expected_database or expected_database in {"postgres", "template0", "template1", "test_db"}:
        raise ValueError("Database does not match the explicitly named application database")
    if not reset_data:
        raise ValueError("This command requires --reset-data after a verified backup")
    if account.get("username") != "krugdev" or account.get("display_name") != "wser220":
        raise ValueError("Unexpected developer account")
    password = account.get("password")
    if not isinstance(password, str) or not 20 <= len(password) <= 100:
        raise ValueError("Provide a generated password of 20–100 characters through stdin")
    async with SessionLocal() as db:
        # Only this application's known tables; never remove schema or Alembic history.
        table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        await db.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY"))
        owner = User(username=account["username"], display_name=account["display_name"],
                     hashed_password=get_password_hash(password), language="ru", bio="")
        db.add(owner)
        await db.flush()
        db.add(Project(
            slug="krug", title="Krug", summary="Сеть для поиска проектов и возможностей для совместной работы.",
            description="", origin="native", owner_id=owner.id, visibility="public",
            status="active", stage="building", tags=["open-source", "web"], skills=["python", "fastapi", "postgresql"],
            source_url="https://github.com/wsersigma228/krug", canonical_url="https://github.com/wsersigma228/krug",
        ))
        await db.commit()
    print("Application data reset; developer account and Krug project created. No updates were authored.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--reset-data", action="store_true")
    args = parser.parse_args()
    account = json.load(sys.stdin)
    asyncio.run(bootstrap(args.expected_database, args.reset_data, account))
