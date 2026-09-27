import asyncio
import sys
from pathlib import Path

from backend.core.db.session import SessionLocal, close_database, create_database_schema
from backend.services.fixture_service import load_users


async def main(path: Path) -> None:
    try:
        await create_database_schema()
        async with SessionLocal() as session:
            await load_users(path, session)
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
