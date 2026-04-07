from __future__ import annotations

import argparse
import asyncio
from datetime import date

import app.db.base  # noqa: F401
from app.db.session import async_session_maker
from app.schemas.payroll import PayrollPolicyOfficialSeedRequest
from app.services.payroll_workflow import (
    PH_OFFICIAL_POLICY_BASELINE_EFFECTIVE_FROM,
    seed_ph_policy_official_core,
)

DEFAULT_VERSION_LABEL = "PH-STATUTORY-ACTIVE-2025"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the current Philippine statutory payroll policy."
    )
    parser.add_argument(
        "--version-label",
        default=DEFAULT_VERSION_LABEL,
        help=f"Policy version label. Defaults to {DEFAULT_VERSION_LABEL}.",
    )
    parser.add_argument(
        "--effective-from",
        type=date.fromisoformat,
        default=PH_OFFICIAL_POLICY_BASELINE_EFFECTIVE_FROM,
        help=(
            "Policy version effective date in YYYY-MM-DD. "
            f"Defaults to {PH_OFFICIAL_POLICY_BASELINE_EFFECTIVE_FROM.isoformat()}."
        ),
    )
    parser.add_argument(
        "--effective-to",
        type=date.fromisoformat,
        default=None,
        help="Optional policy version end date in YYYY-MM-DD.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Replace an existing policy version with the same label.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()

    async with async_session_maker() as session:
        seeded = await seed_ph_policy_official_core(
            session,
            PayrollPolicyOfficialSeedRequest(
                version_label=args.version_label,
                effective_from=args.effective_from,
                effective_to=args.effective_to,
                overwrite_existing=args.overwrite_existing,
            ),
        )

    print("Seeded Philippine statutory payroll policy:")
    print(f"- id: {seeded.id}")
    print(f"- label: {seeded.version_label}")
    print(f"- effective_from: {seeded.effective_from.isoformat()}")
    print(f"- effective_to: {seeded.effective_to.isoformat() if seeded.effective_to else 'None'}")
    print("- includes: SSS 2025 table, PhilHealth 5%, Pag-IBIG current cap, BIR Annex E, NCR-26")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
