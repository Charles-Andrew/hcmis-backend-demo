from __future__ import annotations

import asyncio

import app.db.base  # noqa: F401
from app.db.session import async_session_maker
from app.seeds.performance_questionnaires import import_performance_questionnaires


async def _main() -> None:
    async with async_session_maker() as session:
        created, updated = await import_performance_questionnaires(session)
    print(
        "Imported performance questionnaires: "
        f"{created} created, {updated} updated."
    )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
