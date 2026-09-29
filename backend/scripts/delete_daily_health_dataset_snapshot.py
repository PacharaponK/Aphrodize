"""Explicitly remove one imported daily-health CSV snapshot by its SHA-256 fingerprint."""

from __future__ import annotations

import argparse
import asyncio

from backend.core.db.session import SessionLocal
from backend.services.daily_health_dataset import delete_daily_health_dataset_snapshot


async def _delete(fingerprint: str) -> int:
    async with SessionLocal() as session:
        return await delete_daily_health_dataset_snapshot(session, fingerprint)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fingerprint", help="Exact 64-character SHA-256 snapshot fingerprint")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm deletion of all archived rows belonging to this CSV snapshot",
    )
    args = parser.parse_args()
    if not args.confirm:
        parser.error("Deletion is destructive; pass --confirm after verifying the fingerprint")

    deleted = asyncio.run(_delete(args.fingerprint))
    print(f"Deleted {deleted} imported daily-health rows from snapshot {args.fingerprint}.")


if __name__ == "__main__":
    main()
