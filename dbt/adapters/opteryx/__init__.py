from dbt.adapters.base import AdapterPlugin

from dbt.adapters.opteryx.connections import OpteryxConnectionManager  # noqa: F401
from dbt.adapters.opteryx.connections import OpteryxCredentials
from dbt.adapters.opteryx.impl import OpteryxAdapter
from dbt.include import opteryx

Plugin = AdapterPlugin(
    adapter=OpteryxAdapter,
    credentials=OpteryxCredentials,
    include_path=opteryx.PACKAGE_PATH,
)
