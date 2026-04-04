from __future__ import annotations

import asyncio

from app.scripts.clear_db_data import clear_all_tables_data


async def _main() -> None:
    count = await clear_all_tables_data()
    print(f"Reset database by clearing data from {count} table(s).")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
