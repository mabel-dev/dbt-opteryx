from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional
from typing import Tuple

from dbt.adapters.contracts.connection import AdapterResponse
from dbt.adapters.contracts.connection import Connection
from dbt.adapters.contracts.connection import Credentials
from dbt.adapters.sql import SQLConnectionManager
from dbt_common.exceptions import DbtDatabaseError
from sqlalchemy_dialect import dbapi


@dataclass
class OpteryxCredentials(Credentials):
    # database = Opteryx workspace, schema = collection
    host: str = "opteryx.app"
    port: int = 443
    ssl: bool = True
    user: Optional[str] = None
    token: Optional[str] = None
    timeout: float = 300.0

    _ALIASES = {"workspace": "database", "collection": "schema"}

    @property
    def type(self) -> str:
        return "opteryx"

    @property
    def unique_field(self) -> str:
        return self.host

    def _connection_keys(self) -> Tuple[str, ...]:
        return ("host", "port", "ssl", "user", "database", "schema", "timeout")


class OpteryxConnectionManager(SQLConnectionManager):
    TYPE = "opteryx"

    @contextmanager
    def exception_handler(self, sql: str):
        try:
            yield
        except dbapi.Error as e:
            raise DbtDatabaseError(str(e)) from e

    @classmethod
    def open(cls, connection: Connection) -> Connection:
        if connection.state == "open":
            return connection
        creds = connection.credentials
        connection.handle = dbapi.connect(
            host=creds.host,
            port=creds.port,
            username=creds.user,
            token=creds.token,
            ssl=creds.ssl,
            timeout=creds.timeout,
        )
        connection.state = "open"
        return connection

    def cancel(self, connection: Connection) -> None:
        # OpteryxAdapter.is_cancelable() is False, so dbt never calls this.
        raise NotImplementedError("dbt-opteryx does not cancel in-flight queries")

    @classmethod
    def get_response(cls, cursor) -> AdapterResponse:
        return AdapterResponse(
            _message="OK", rows_affected=cursor.rowcount, query_id=cursor.statement_handle
        )

    # Opteryx has no transactions: every statement commits on its own. dbt still
    # brackets work in begin/commit, so these send nothing to the server.
    def add_begin_query(self):
        pass

    def add_commit_query(self):
        pass
