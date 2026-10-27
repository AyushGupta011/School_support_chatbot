"""add chat persistence and actions

Revision ID: 002
Revises: 001
Create Date: 2026-10-25 21:00:00.000000

"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: str | None = '001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns to unanswered_queries
    op.add_column('unanswered_queries', sa.Column('status', sa.String(), server_default='pending', nullable=False))
    op.add_column('unanswered_queries', sa.Column('resolution', sa.Text(), nullable=True))
    op.add_column('unanswered_queries', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))

    # Create chat_sessions
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), server_default='New Conversation', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_sessions_id'), 'chat_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_student_id'), 'chat_sessions', ['student_id'], unique=False)

    # Create chat_messages
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)

    # Create leave_applications
    op.create_table(
        'leave_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.String(), nullable=False),
        sa.Column('end_date', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), server_default='submitted', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leave_applications_id'), 'leave_applications', ['id'], unique=False)
    op.create_index(op.f('ix_leave_applications_student_id'), 'leave_applications', ['student_id'], unique=False)

    # Create faculty_appointments
    op.create_table(
        'faculty_appointments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('faculty_id', sa.Integer(), nullable=True),
        sa.Column('faculty_name', sa.String(), nullable=False),
        sa.Column('appointment_date', sa.String(), nullable=False),
        sa.Column('appointment_time', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), server_default='confirmed', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['faculty_id'], ['faculty.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_faculty_appointments_id'), 'faculty_appointments', ['id'], unique=False)
    op.create_index(op.f('ix_faculty_appointments_student_id'), 'faculty_appointments', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_table('faculty_appointments')
    op.drop_table('leave_applications')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_column('unanswered_queries', 'resolved_at')
    op.drop_column('unanswered_queries', 'resolution')
    op.drop_column('unanswered_queries', 'status')
