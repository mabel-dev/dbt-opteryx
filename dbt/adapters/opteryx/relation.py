from dataclasses import dataclass

from dbt.adapters.base.relation import BaseRelation


@dataclass(frozen=True, eq=False, repr=False)
class OpteryxRelation(BaseRelation):
    def render_limited(self) -> str:
        # `--empty` renders a ref as `(select * from x where false limit 0)`, and
        # Opteryx refuses a bare literal as a WHERE clause.
        if self.limit == 0:
            return f"(select * from {self.render()} where 1 = 0 limit 0){self._render_limited_alias()}"
        return super().render_limited()
