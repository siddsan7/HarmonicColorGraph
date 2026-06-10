"""phase 1 core schema

Revision ID: 0001_phase1_core_schema
Revises:
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_phase1_core_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chords",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("root", sa.String(), nullable=True),
        sa.Column("quality", sa.String(), nullable=True),
        sa.Column("pitch_classes", sa.JSON(), nullable=True),
        sa.Column("intervals", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_chords_symbol", "chords", ["symbol"], unique=True)

    op.create_table(
        "roman_chords",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("roman", sa.String(), nullable=False),
        sa.Column("scale_degree", sa.Integer(), nullable=True),
        sa.Column("quality", sa.String(), nullable=True),
        sa.Column("mode_context", sa.String(), nullable=True),
        sa.Column("borrowed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("borrowed_from", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_roman_chords_roman", "roman_chords", ["roman"], unique=True)

    op.create_table(
        "progressions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_song_id", sa.String(), nullable=True),
        sa.Column("key", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("genre", sa.String(), nullable=True),
        sa.Column("subgenre", sa.String(), nullable=True),
        sa.Column("section", sa.String(), nullable=True),
        sa.Column("absolute_chords", sa.JSON(), nullable=True),
        sa.Column("roman_chords", sa.JSON(), nullable=True),
        sa.Column("analysis_confidence", sa.Float(), nullable=True),
        sa.Column("parse_warnings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "progression_chords",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("progression_id", sa.Integer(), sa.ForeignKey("progressions.id")),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("absolute_chord", sa.String(), nullable=False),
        sa.Column("roman_chord", sa.String(), nullable=True),
    )

    op.create_table(
        "transitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_roman", sa.String(), nullable=False),
        sa.Column("to_roman", sa.String(), nullable=False),
        sa.Column("mode_context", sa.String(), nullable=True),
        sa.Column("genre", sa.String(), nullable=True),
        sa.Column("subgenre", sa.String(), nullable=True),
        sa.Column("section", sa.String(), nullable=True),
        sa.Column("decade", sa.Integer(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.Column("relationship_labels", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_transitions_from_roman", "transitions", ["from_roman"])
    op.create_index("ix_transitions_to_roman", "transitions", ["to_roman"])

    op.create_table(
        "songs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("artist", sa.String(), nullable=True),
        sa.Column("spotify_id", sa.String(), nullable=True),
        sa.Column("genre", sa.String(), nullable=True),
        sa.Column("release_date", sa.String(), nullable=True),
    )
    op.create_index("ix_songs_source_id", "songs", ["source_id"], unique=True)

    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        "theory_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "transition_theory_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transition_id", sa.Integer(), sa.ForeignKey("transitions.id")),
        sa.Column("theory_label_id", sa.Integer(), sa.ForeignKey("theory_labels.id")),
    )
    op.create_table(
        "source_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
    )
    op.create_index("ix_source_metadata_source_id", "source_metadata", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_source_metadata_source_id", table_name="source_metadata")
    op.drop_table("source_metadata")
    op.drop_table("transition_theory_labels")
    op.drop_table("theory_labels")
    op.drop_table("sections")
    op.drop_table("genres")
    op.drop_index("ix_songs_source_id", table_name="songs")
    op.drop_table("songs")
    op.drop_index("ix_transitions_to_roman", table_name="transitions")
    op.drop_index("ix_transitions_from_roman", table_name="transitions")
    op.drop_table("transitions")
    op.drop_table("progression_chords")
    op.drop_table("progressions")
    op.drop_index("ix_roman_chords_roman", table_name="roman_chords")
    op.drop_table("roman_chords")
    op.drop_index("ix_chords_symbol", table_name="chords")
    op.drop_table("chords")
