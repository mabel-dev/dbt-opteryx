"""Offline checks of the adapter: no connection to opteryx.app is made."""

from pathlib import Path

import pytest
from dbt_common.clients import agate_helper
from dbt.adapters.opteryx import Plugin
from dbt.adapters.opteryx.connections import OpteryxConnectionManager
from dbt.adapters.opteryx.connections import OpteryxCredentials
from dbt.adapters.opteryx.impl import OpteryxAdapter

PROJECT = Path(__file__).parent.parent / "integration" / "project"


def test_plugin_registers_the_opteryx_adapter():
    assert Plugin.adapter is OpteryxAdapter
    assert Plugin.credentials is OpteryxCredentials
    assert (Path(Plugin.include_path) / "macros" / "adapters.sql").is_file()


def test_workspace_and_collection_alias_database_and_schema():
    creds = OpteryxCredentials.from_dict(
        OpteryxCredentials.translate_aliases(
            {"workspace": "personal", "collection": "alice", "user": "alice", "token": "t"}
        )
    )
    assert (creds.database, creds.schema) == ("personal", "alice")
    assert creds.type == "opteryx"
    assert (creds.host, creds.port, creds.ssl) == ("opteryx.app", 443, True)


def test_seed_types_are_ones_opteryx_cast_accepts():
    # dbt's own type inference, as seeds use it.
    table = agate_helper.table_from_rows(
        [
            ["a", "7", "1.5", "true", "2024-01-01", "2024-01-01 10:00:00"],
            ["b", "42", "2.25", "false", "2024-01-02", "2024-01-02 11:00:00"],
        ],
        ["text", "int", "float", "bool", "date", "ts"],
    )
    assert [OpteryxAdapter.convert_type(table, i) for i in range(6)] == [
        "VARCHAR",
        "INTEGER",
        "FLOAT",
        "BOOLEAN",
        "DATE",
        "TIMESTAMP",
    ]


def test_declared_incremental_strategies():
    assert OpteryxAdapter.valid_incremental_strategies(None) == ["append", "merge", "delete+insert"]


def test_cancel_is_refused_not_ignored():
    assert OpteryxAdapter.is_cancelable() is False
    with pytest.raises(NotImplementedError):
        OpteryxConnectionManager.cancel(None, None)


def test_integration_project_parses(tmp_path, monkeypatch):
    from dbt.cli.main import dbtRunner

    for name, value in {
        "OPTERYX_USER": "unit",
        "OPTERYX_TOKEN": "unit",
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }.items():
        monkeypatch.setenv(name, value)
    result = dbtRunner().invoke(
        [
            "parse",
            "--project-dir", str(PROJECT),
            "--profiles-dir", str(PROJECT),
            "--target-path", str(tmp_path / "target"),
            "--log-path", str(tmp_path / "logs"),
        ]
    )
    assert result.success, result.exception
