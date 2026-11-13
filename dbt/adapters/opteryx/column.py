from dbt.adapters.base.column import Column


class OpteryxColumn(Column):
    # Opteryx CAST refuses dbt's default `character varying(n)`; unit-test fixtures cast with this.
    @classmethod
    def string_type(cls, size: int) -> str:
        return "VARCHAR"
