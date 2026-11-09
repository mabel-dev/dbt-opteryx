from dbt.adapters.sql import SQLAdapter

from dbt.adapters.opteryx.connections import OpteryxConnectionManager


class OpteryxAdapter(SQLAdapter):
    ConnectionManager = OpteryxConnectionManager

    @classmethod
    def date_function(cls) -> str:
        return "now()"

    @classmethod
    def is_cancelable(cls) -> bool:
        return False

    def valid_incremental_strategies(self):
        return ["append", "merge", "delete+insert"]

    # Seed column types. Opteryx CAST refuses dbt's defaults (`text`, `float8`).
    @classmethod
    def convert_text_type(cls, agate_table, col_idx) -> str:
        return "VARCHAR"

    @classmethod
    def convert_number_type(cls, agate_table, col_idx) -> str:
        import agate  # dbt imports agate lazily; follow suit

        decimals = agate_table.aggregate(agate.MaxPrecision(col_idx))
        return "FLOAT" if decimals else "INTEGER"

    @classmethod
    def convert_integer_type(cls, agate_table, col_idx) -> str:
        return "INTEGER"

    @classmethod
    def convert_boolean_type(cls, agate_table, col_idx) -> str:
        return "BOOLEAN"

    @classmethod
    def convert_datetime_type(cls, agate_table, col_idx) -> str:
        return "TIMESTAMP"

    @classmethod
    def convert_date_type(cls, agate_table, col_idx) -> str:
        return "DATE"

    @classmethod
    def convert_time_type(cls, agate_table, col_idx) -> str:
        return "TIME"
