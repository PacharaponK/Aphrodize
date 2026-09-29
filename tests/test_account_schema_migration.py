from types import SimpleNamespace

import pytest

from backend.core.db import session as db_session


@pytest.mark.asyncio
async def test_startup_adds_missing_account_columns_without_dropping_data(monkeypatch) -> None:
    statements = []

    class Connection:
        dialect = SimpleNamespace(name="postgresql")

        async def run_sync(self, _callback):
            return None

        async def scalar(self, _statement):
            return "CHECK (sleep_duration_minutes <= 600)"

        async def execute(self, statement):
            statements.append(str(statement))

    class Context:
        async def __aenter__(self):
            return Connection()

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(db_session, "engine", SimpleNamespace(begin=Context))
    await db_session.create_database_schema()

    assert not any("DROP TABLE" in s for s in statements)
    assert any("ADD COLUMN IF NOT EXISTS status" in s for s in statements)
    assert any("ADD COLUMN IF NOT EXISTS deleted_at" in s for s in statements)
    assert any("ADD CONSTRAINT ck_users_status" in s for s in statements)
    account_statements = [s for s in statements if s.startswith("ALTER TABLE accounts")]
    assert len(account_statements) == 6
    assert all("ADD COLUMN IF NOT EXISTS" in s for s in account_statements)
    assert any("failed_login_count INTEGER NOT NULL DEFAULT 0" in s for s in account_statements)
    assert any("updated_at TIMESTAMPTZ NOT NULL DEFAULT now()" in s for s in account_statements)
