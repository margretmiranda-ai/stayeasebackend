"""Remove the JWT token blocklist.

Revision ID: ab41d7c92e60
Revises: f7c13a2d9e64
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa


revision = "ab41d7c92e60"
down_revision = "f7c13a2d9e64"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_token_blocklist_expires_at", table_name="token_blocklist")
    op.drop_table("token_blocklist")


def downgrade():
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
