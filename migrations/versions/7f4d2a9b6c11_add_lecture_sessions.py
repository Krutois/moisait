"""Add lecture sessions

Revision ID: 7f4d2a9b6c11
Revises: 29a40a1dc942
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa


revision = "7f4d2a9b6c11"
down_revision = "29a40a1dc942"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lecture_sessions",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("words", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lecture_sessions_created_at"), "lecture_sessions", ["created_at"], unique=False)
    op.create_index(op.f("ix_lecture_sessions_expires_at"), "lecture_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_lecture_sessions_owner_id"), "lecture_sessions", ["owner_id"], unique=False)
    op.create_index(op.f("ix_lecture_sessions_status"), "lecture_sessions", ["status"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_lecture_sessions_status"), table_name="lecture_sessions")
    op.drop_index(op.f("ix_lecture_sessions_owner_id"), table_name="lecture_sessions")
    op.drop_index(op.f("ix_lecture_sessions_expires_at"), table_name="lecture_sessions")
    op.drop_index(op.f("ix_lecture_sessions_created_at"), table_name="lecture_sessions")
    op.drop_table("lecture_sessions")
