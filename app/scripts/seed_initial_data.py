from __future__ import annotations

import asyncio

import app.db.base  # noqa: F401
from app.db.session import async_session_maker
from app.seeds.initial_data import seed_initial_data


async def _main() -> None:
    async with async_session_maker() as session:
        await seed_initial_data(session)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
