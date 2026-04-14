"""compat placeholder for removed certificate attendance type migration

Revision ID: 0047_cert_att_type
Revises: 0046_cert_att_punch_time
Create Date: 2026-04-14 00:00:00.000000
"""

from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "0047_cert_att_type"
down_revision: str | None = "0046_cert_att_punch_time"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Intentionally no-op. The temporary `type` field change was reverted.
    return None


def downgrade() -> None:
    return None
