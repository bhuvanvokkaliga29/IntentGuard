"""Initial database schema for IntentGuard

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table: mandates ──────────────────────────────────────────
    op.create_table(
        'mandates',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('intent_text', sa.Text(), nullable=False),
        sa.Column('max_amount_per_txn', sa.Float(), nullable=False),
        sa.Column('budget_cap', sa.Float(), nullable=True),
        sa.Column('allowed_categories', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('allowed_merchants', sa.Text(), nullable=True),
        sa.Column('frequency', sa.String(length=50), nullable=False, server_default='on_demand'),
        sa.Column('exclusions', sa.Text(), nullable=True),
        sa.Column('location_constraint', sa.String(length=100), nullable=True),
        sa.Column('purpose_context', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # ── Table: transactions ──────────────────────────────────────
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('mandate_id', sa.String(length=36), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('merchant_name', sa.String(length=255), nullable=False),
        sa.Column('merchant_category', sa.String(length=255), nullable=False),
        sa.Column('item_description', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('ground_truth_tier', sa.String(length=50), nullable=True),
        sa.Column('ground_truth_reason', sa.Text(), nullable=True),
    )

    # ── Table: decisions ─────────────────────────────────────────
    op.create_table(
        'decisions',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('mandate_id', sa.String(length=36), nullable=False, server_default=''),
        sa.Column('structural_check_result', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('extracted_facts', sa.Text(), nullable=True),
        sa.Column('semantic_judgment', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('final_decision', sa.String(length=20), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('prompt_version', sa.String(length=20), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('audit_id', sa.String(length=36), nullable=True),
        sa.Column('human_review_status', sa.String(length=50), nullable=True),
        sa.Column('human_review_notes', sa.Text(), nullable=True),
        sa.Column('human_reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # ── Table: audit_logs ────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('decision_id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('mandate_id', sa.String(length=36), nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('final_decision', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('signature', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('decisions')
    op.drop_table('transactions')
    op.drop_table('mandates')
