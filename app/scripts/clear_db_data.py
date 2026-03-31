from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.db.session import engine


async def clear_all_tables_data() -> int:
    """Truncate all public tables except Alembic metadata."""
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename <> 'alembic_version'
                ORDER BY tablename
                """
            )
        )
        table_names = [row[0] for row in result.fetchall()]

        if not table_names:
            return 0

        quoted_tables = ", ".join(f'"{name}"' for name in table_names)
        await connection.execute(
            text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE")
        )

    return len(table_names)


async def _main() -> None:
    count = await clear_all_tables_data()
    print(f"Cleared data from {count} table(s).")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
