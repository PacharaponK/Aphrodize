from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from backend.core.db.models import Account, AccountRole, AuthSession, AuthToken, LoginAudit, User


def test_auth_account_tables_keep_identity_and_security_records_separate() -> None:
    assert User.__tablename__ == "users"
    assert Account.__table__.c.user_id.unique is True
    assert {AccountRole.__tablename__, AuthSession.__tablename__, AuthToken.__tablename__, LoginAudit.__tablename__} == {
        "account_roles",
        "auth_sessions",
        "auth_tokens",
        "login_audit",
    }


def test_auth_account_schema_has_critical_constraints_and_indexes() -> None:
    role_constraints = [constraint for constraint in AccountRole.__table__.constraints if isinstance(constraint, UniqueConstraint)]
    assert any(tuple(column.name for column in constraint.columns) == ("account_id", "role") for constraint in role_constraints)

    token_constraints = [constraint for constraint in AuthToken.__table__.constraints if isinstance(constraint, CheckConstraint)]
    assert any(constraint.name == "ck_auth_tokens_purpose" for constraint in token_constraints)

    user_constraints = [constraint for constraint in User.__table__.constraints if isinstance(constraint, CheckConstraint)]
    assert any(constraint.name == "ck_users_status" for constraint in user_constraints)

    session_indexes = [index for index in AuthSession.__table__.indexes if isinstance(index, Index)]
    assert any(index.name == "ix_auth_sessions_account_active" for index in session_indexes)
    assert AuthSession.__table__.c.refresh_token_hash.unique is True
    assert AuthToken.__table__.c.token_hash.unique is True
