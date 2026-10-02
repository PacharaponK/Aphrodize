"""Import the current sandbox dataset into the database's provenance archive."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from backend.core.db.session import SessionLocal, create_database_schema
from backend.services.daily_health_dataset import import_daily_health_dataset

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = (
    REPOSITORY_ROOT
    / "sandboxes"
    / "datamake"
    / "output"
    / "lifestyle_medically_cautious_sleepmax540_forecast_with_real_user.csv"
)


async def _import(dataset_path: Path) -> dict[str, int | str]:
    await create_database_schema()
    async with SessionLocal() as session:
        return await import_daily_health_dataset(session, dataset_path=dataset_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        default=DEFAULT_DATASET,
        help="CSV path (defaults to the latest medically cautious sandbox dataset)",
    )
    args = parser.parse_args()
    if not args.dataset.is_file():
        parser.error(f"Dataset file not found: {args.dataset}")

    summary = asyncio.run(_import(args.dataset))
    print(
        "Imported daily-health dataset snapshot: "
        f"read={summary['rows_read']} inserted={summary['rows_inserted']} "
        f"fingerprint={summary['dataset_fingerprint']}"
    )
    print("Imported rows remain excluded from user-model training until individually reviewed.")


if __name__ == "__main__":
    main()
