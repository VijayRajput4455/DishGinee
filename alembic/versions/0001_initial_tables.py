"""initial_tables

Revision ID: 0001_initial_tables
Revises: 
Create Date: 2026-07-24 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums
    input_type_enum = postgresql.ENUM('IMAGE', 'TEXT', 'VOICE', name='inputtype', create_type=False)
    input_type_enum.create(op.get_bind(), checkfirst=True)

    request_status_enum = postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='requeststatus', create_type=False)
    request_status_enum.create(op.get_bind(), checkfirst=True)

    image_status_enum = postgresql.ENUM('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED', name='imagestatus', create_type=False)
    image_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create 'requests' table
    op.create_table(
        'requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('input_type', sa.Enum('IMAGE', 'TEXT', 'VOICE', name='inputtype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='requeststatus'), nullable=False),
        sa.Column('raw_text_input', sa.Text(), nullable=True),
        sa.Column('audio_url', sa.String(length=500), nullable=True),
        sa.Column('audio_transcription', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_requests_id'), 'requests', ['id'], unique=False)

    # 3. Create 'request_images' table
    op.create_table(
        'request_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('original_image', sa.String(length=500), nullable=False),
        sa.Column('annotated_image', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED', name='imagestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_request_images_id'), 'request_images', ['id'], unique=False)

    # 4. Create 'request_outputs' table
    op.create_table(
        'request_outputs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('ingredients', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('selected_recipe', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cooking_guide', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id')
    )
    op.create_index(op.f('ix_request_outputs_id'), 'request_outputs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_request_outputs_id'), table_name='request_outputs')
    op.drop_table('request_outputs')
    op.drop_index(op.f('ix_request_images_id'), table_name='request_images')
    op.drop_table('request_images')
    op.drop_index(op.f('ix_requests_id'), table_name='requests')
    op.drop_table('requests')

    image_status_enum = postgresql.ENUM('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED', name='imagestatus')
    image_status_enum.drop(op.get_bind(), checkfirst=True)

    request_status_enum = postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='requeststatus')
    request_status_enum.drop(op.get_bind(), checkfirst=True)

    input_type_enum = postgresql.ENUM('IMAGE', 'TEXT', 'VOICE', name='inputtype')
    input_type_enum.drop(op.get_bind(), checkfirst=True)
