import argparse
import asyncio
from pathlib import Path

from backend.core.db.session import SessionLocal, close_database, create_database_schema
from backend.services.fixture_service import load_products, load_users


async def main(path: Path, *, products: bool = False) -> None:
    try:
        await create_database_schema()
        async with SessionLocal() as session:
            if products:
                inserted = await load_products(path, session)
                print(f"Imported {inserted} products; existing catalog rows were kept.")
            else:
                await load_users(path, session)
    finally:
        await close_database()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load local demo fixtures without duplicates.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--products", action="store_true", help="Load only the product catalog")
    args = parser.parse_args()
    asyncio.run(main(args.path, products=args.products))
