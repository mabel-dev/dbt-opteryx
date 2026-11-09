"""Runs the dbt feature matrix against opteryx.app and checks every outcome.

Needs CLIENT_ID and CLIENT_SECRET; writes into personal.<CLIENT_ID> unless
OPTERYX_WORKSPACE / OPTERYX_COLLECTION say otherwise.

Every step runs. Each node (or, for steps without nodes, the step itself) must pass
unless it is listed in EXPECTED_FAILURES, in which case it must fail. An expected
failure that passes is reported too, so the list is pruned as gaps close.
"""

import os
import sys
from pathlib import Path

from dbt.cli.main import dbtRunner

PROJECT = Path(__file__).parent / "project"

# (label, dbt arguments, reports per node)
STEPS = [
    ("debug", ["debug"], False),
    ("seed-full", ["seed", "--full-refresh"], True),
    ("run-full", ["run", "--full-refresh"], True),
    ("seed", ["seed"], True),  # re-seed over an existing table
    ("run", ["run"], True),  # second pass: table swap + incremental paths
    ("test", ["test"], True),
    ("snapshot-1", ["snapshot"], True),
    ("snapshot-2", ["snapshot"], True),  # second pass: change detection
    ("freshness", ["source", "freshness"], True),
    ("show", ["show", "--select", "customers_by_country"], False),
    ("run-operation", ["run-operation", "row_count", "--args", "{relation_name: customers}"], False),
    ("run-empty", ["run", "--empty"], True),
    ("docs", ["docs", "generate"], False),
]

# "<step>:<node name>" or "<step>" -> why it fails (issue numbers are the README's).
EXPECTED_FAILURES = {
    "run-full:customers_contract": "adapter refuses enforced contracts",
    "run-full:active_customers": "#13 CTAS cannot see its WITH body",
    "run:customers_contract": "adapter refuses enforced contracts",
    "run:active_customers": "#13 CTAS cannot see its WITH body",
}

PASSED = {"success", "pass"}


def outcomes():
    os.environ["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    for label, args, per_node in STEPS:
        print(f"\n=== {label}: dbt {' '.join(args)}", flush=True)
        res = dbtRunner().invoke([*args, "--project-dir", str(PROJECT), "--profiles-dir", str(PROJECT)])
        if per_node and res.result is not None:
            for r in res.result.results:
                yield f"{label}:{r.node.name}", str(r.status) in PASSED
        else:
            yield label, res.success


def main():
    seen = dict(outcomes())
    rows = []
    for key, ok in seen.items():
        reason = EXPECTED_FAILURES.get(key)
        if reason is None:
            rows.append(("PASS" if ok else "FAIL", key, ""))
        else:
            rows.append(("XPASS" if ok else "xfail", key, reason))
    for key in EXPECTED_FAILURES.keys() - seen.keys():
        rows.append(("MISSING", key, "expected failure never ran"))

    print("\n=== outcomes")
    for status, key, reason in rows:
        print(f"{status:8} {key}{'  (' + reason + ')' if reason else ''}")
    bad = [r for r in rows if r[0] in ("FAIL", "XPASS", "MISSING")]
    print(f"\n{len(rows) - len(bad)} as expected, {len(bad)} not")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
