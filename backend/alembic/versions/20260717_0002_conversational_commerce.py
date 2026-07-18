"""Add sports catalog fields and anonymous conversations.

Revision ID: 20260717_0002
Revises: 20260717_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0002"
down_revision: str | None = "20260717_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("sku", sa.String(64), nullable=True))
    op.add_column("products", sa.Column("sport", sa.String(80), nullable=True))
    op.add_column("products", sa.Column("brand", sa.String(120), nullable=True))
    op.add_column(
        "products",
        sa.Column(
            "specifications",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column("in_stock", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    # Existing installations have the original eight rows. Stable values make
    # the migration safe before the idempotent seed command enriches them.
    op.execute(
        """
        UPDATE products SET
          sku = 'LEGACY-' || lpad(id::text, 6, '0'),
          sport = CASE category
            WHEN 'Footwear' THEN 'Running' WHEN 'Fitness' THEN 'Fitness'
            WHEN 'Outdoors' THEN 'Hiking' ELSE 'Multisport' END,
          brand = retailer
        WHERE sku IS NULL
        """
    )
    op.alter_column("products", "sku", nullable=False)
    op.alter_column("products", "sport", nullable=False)
    op.alter_column("products", "brand", nullable=False)
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_sport", "products", ["sport"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_in_stock", "products", ["in_stock"])

    op.create_table(
        "conversation_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(20), nullable=True),
        sa.Column(
            "envelope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["conversation_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_id", "request_id", name="uq_message_thread_request"
        ),
    )
    op.create_index(
        "ix_conversation_messages_thread_id",
        "conversation_messages",
        ["thread_id"],
    )


def downgrade() -> None:
    op.drop_table("conversation_messages")
    op.drop_table("conversation_threads")
    for index in (
        "ix_products_in_stock",
        "ix_products_brand",
        "ix_products_sport",
        "ix_products_sku",
    ):
        op.drop_index(index, table_name="products")
    for column in ("in_stock", "specifications", "brand", "sport", "sku"):
        op.drop_column("products", column)
