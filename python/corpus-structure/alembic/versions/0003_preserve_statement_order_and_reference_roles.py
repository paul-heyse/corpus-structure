"""Preserve statement order and unresolved reference roles.

Generated from model 0.5.0 and reviewed: widen the entity-reference role CHECK and add
the nullable first-sentence ordinal. Existing materializations remain unchanged.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29 01:40:18.134133
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | Sequence[str] | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
# the model revision (content hash) this migration realizes (core/db/migrations.py)
model_revision: str = '10c8462e734f6c89d33f3898a6fd242c825dc5cac79b1eb66552bd142886c8b1'


def upgrade() -> None:
    op.drop_constraint(op.f('ck_claim_entity_ref_role_ba4aa55429'), 'claim_entity_ref', schema='kb', type_='check')
    op.create_check_constraint(op.f('ck_claim_entity_ref_role_0cb7a3a712'), 'claim_entity_ref', "role IN ('binding_family_param', 'binding_param', 'binding_variable', 'condition_premise', 'pred_arg', 'qualifier')", schema='kb')
    op.add_column('entity', sa.Column('statement_ordinal', sa.Integer(), nullable=True), schema='kb')


def downgrade() -> None:
    op.drop_column('entity', 'statement_ordinal', schema='kb')
    op.drop_constraint(op.f('ck_claim_entity_ref_role_0cb7a3a712'), 'claim_entity_ref', schema='kb', type_='check')
    op.create_check_constraint(op.f('ck_claim_entity_ref_role_ba4aa55429'), 'claim_entity_ref', "role = ANY (ARRAY['binding_family_param'::text, 'binding_variable'::text, 'pred_arg'::text, 'qualifier'::text])", schema='kb')
