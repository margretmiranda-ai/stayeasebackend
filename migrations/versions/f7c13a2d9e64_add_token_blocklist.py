"""Add JWT token blocklist.

Revision ID: f7c13a2d9e64
Revises: 8c4e85f047f9
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa


revision = "f7c13a2d9e64"
down_revision = "8c4e85f047f9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_blocklist",
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index(
        "ix_token_blocklist_expires_at",
        "token_blocklist",
        ["expires_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_token_blocklist_expires_at", table_name="token_blocklist")
    op.drop_table("token_blocklist")
