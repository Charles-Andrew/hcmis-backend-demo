"""fix bridge commands id sequence

Revision ID: 0012_bridge_cmd_id_seq
Revises: 0011_bridge_commands
Create Date: 2026-04-03 00:00:06.000000
"""

from alembic import op


revision = "0012_bridge_cmd_id_seq"
down_revision = "0011_bridge_commands"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'bridge_commands'
            ) THEN
                CREATE SEQUENCE IF NOT EXISTS bridge_commands_id_seq
                    OWNED BY bridge_commands.id;

                ALTER TABLE bridge_commands
                    ALTER COLUMN id SET DEFAULT nextval('bridge_commands_id_seq');

                PERFORM setval(
                    'bridge_commands_id_seq',
                    COALESCE((SELECT MAX(id) FROM bridge_commands), 0) + 1,
                    false
                );
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'bridge_commands'
            ) THEN
                ALTER TABLE bridge_commands ALTER COLUMN id DROP DEFAULT;
            END IF;
        END $$;
        """
    )
