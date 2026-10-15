"""The assistant's search index over notes, history, activities, call notes and opportunities.

Keyword search (Postgres full text) always works. Meaning search needs the pgvector extension: if it's
available the embedding column and index are added; if not, the assistant searches by keyword only and
nothing else changes. Re-running this after installing pgvector isn't needed - see app/brain/search.py
(ensure_vector), which adds the column the first time it finds the extension.

Revision ID: 0060
Revises: 0059
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0060"
down_revision: str | None = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brain_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(20), nullable=False),     # note | history | activity | call | opportunity
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("part", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), index=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), index=True),
        sa.Column("source_db", sa.String(64)),
        sa.Column("private_to", postgresql.UUID(as_uuid=True)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), index=True),
        sa.Column("header", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("hash", sa.String(32), nullable=False),
        sa.Column("embedded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_type", "source_id", "part", name="uq_brain_chunk_source"),
    )
    op.execute("ALTER TABLE brain_chunks ADD COLUMN tsv tsvector GENERATED ALWAYS AS "
               "(to_tsvector('english', coalesce(header, '') || ' ' || coalesce(body, ''))) STORED")
    op.execute("CREATE INDEX ix_brain_chunks_tsv ON brain_chunks USING gin (tsv)")
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
        BEGIN
          CREATE EXTENSION IF NOT EXISTS vector;
          ALTER TABLE brain_chunks ADD COLUMN IF NOT EXISTS embedding vector(768);
          CREATE INDEX IF NOT EXISTS ix_brain_chunks_embedding ON brain_chunks USING hnsw (embedding vector_cosine_ops);
        EXCEPTION WHEN OTHERS THEN
          RAISE NOTICE 'pgvector could not be enabled (%), keyword search only', SQLERRM;
        END;
      END IF;
    END $$;
    """)


def downgrade() -> None:
    op.drop_table("brain_chunks")
