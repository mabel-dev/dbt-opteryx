# dbt-opteryx

dbt adapter for [Opteryx Cloud](https://opteryx.app). It runs dbt Core 1.x against
Opteryx's HTTP jobs API, using the DBAPI from
[`opteryx-sqlalchemy`](https://pypi.org/project/opteryx-sqlalchemy/).

## Install

```bash
pip install dbt-opteryx
```

## Profile

dbt's `database` is an Opteryx **workspace** and `schema` is a **collection**
(`workspace` / `collection` are accepted as aliases). Every account has a personal
space, `personal.<your user>`, which needs no setup:

```yaml
my_project:
  target: cloud
  outputs:
    cloud:
      type: opteryx
      host: opteryx.app
      port: 443
      ssl: true
      user: "{{ env_var('OPTERYX_USER') }}"
      token: "{{ env_var('OPTERYX_TOKEN') }}"
      database: personal            # workspace
      schema: "{{ env_var('OPTERYX_USER') }}"  # collection
      threads: 1
```

Put this in `dbt_project.yml` until the leading-comment fix in opteryx-core is deployed:

```yaml
query-comment:
  append: true
```

## Behaviour to know about

- **No transactions.** Opteryx has none; every statement commits on its own. The
  adapter sends nothing for dbt's BEGIN/COMMIT.
- **No temporary tables.** dbt's `__dbt_tmp` intermediates are real tables, which
  dbt drops when the model succeeds. A failed model can leave one behind.
- **Views** are built with `CREATE OR REPLACE VIEW`, not dbt's rename swap.
- **Seeds** are inserted as typed literals (`CAST('…' AS <type>)`), not bind
  parameters.
- **Incremental strategies:** `append`, `merge` and `delete+insert`.
- **Model contracts are refused**, with an error naming the model: the adapter does
  not enforce them yet, and ignoring one silently would claim a guarantee it does not keep.
- **Queries cannot be cancelled** from dbt.
- **Empty relations filter on `WHERE 1 = 0`.** Opteryx refuses a bare literal as a
  WHERE clause, so the adapter replaces dbt's `WHERE false` in `--empty` refs and in
  the schema-only subquery dbt uses for unit tests and column introspection.
- **Snapshots do not work.** dbt's snapshot SQL selects `*, <columns>`, which
  Opteryx refuses (`SELECT t.*, <columns>` is accepted). See issue 14.

## Integration tests

`tests/integration/project` is a dbt project covering seeds, sources (including
freshness), view, table, ephemeral and incremental models (all three strategies),
snapshots, hooks, contracts, generic, singular and unit tests, `show`,
`run-operation`, `--empty` and docs generation. Run it against opteryx.app:

```bash
CLIENT_ID=… CLIENT_SECRET=… python tests/integration/run.py
```

Every step runs, and every node must pass except those listed in
`EXPECTED_FAILURES` in `run.py`, which must fail. The run fails on an unexpected
failure and also on an expected failure that passes, so the list is pruned as
Opteryx gaps close.

It writes into `personal.$CLIENT_ID` (override with `OPTERYX_WORKSPACE` /
`OPTERYX_COLLECTION`). CI runs it on push (`.github/workflows/integration.yaml`),
reading `CLIENT_ID` / `CLIENT_SECRET` from the `OPTERYX_TEST_CLIENT` /
`OPTERYX_TEST_TOKEN` repository secrets. That is a service account, which has no
personal space, so CI writes into `opteryx_ci.dbt`.

Offline checks (no connection) run with `python -m pytest tests/unit`.

## CI

| Workflow | Runs on | Does |
|---|---|---|
| `regression-tests.yaml` | push | `tests/unit` on Python 3.10–3.14 × dbt-core 1.10 (floor) and latest; 1.10 is skipped on 3.14, where it cannot import |
| `integration.yaml` | push | `tests/integration/run.py` against opteryx.app; known gaps are expected failures |
| `semgrep_scan.yaml` | push | Semgrep scan, findings uploaded to `opteryx.ops.sast_findings` |
| `release.yaml` | `v*` tag | Builds and publishes to PyPI by trusted publishing |

Repository secrets: `OPTERYX_TEST_CLIENT`, `OPTERYX_TEST_TOKEN` (integration),
`UPLOAD_CLIENT`, `UPLOAD_TOKEN` (Semgrep upload).

## Releasing

Bump `version` in `dbt/adapters/opteryx/__version__.py` (the package version is read
from it), then push a matching `vX.Y.Z` tag. PyPI must list this repository's
`release.yaml` as a trusted publisher for `dbt-opteryx`; for the first release that
is a pending publisher, set up on PyPI before the tag is pushed.

## Verification against opteryx.app (2026-11-09)

dbt-core 1.12.6, dbt-adapters 1.24.5, opteryx-sqlalchemy 0.0.13.

| Feature | Result | Notes |
|---|---|---|
| `dbt debug` | PASS | |
| Seeds, first load | PASS | Needs the typed-literal loader in this adapter |
| Seeds, reload over an existing table | PASS | Verified 2026-11-10 after the TRUNCATE fix deployed |
| Seeds, `--full-refresh` | PASS | Drops and recreates |
| Sources: `source()` reads | PASS | `samples.tpch_sf001.nation` |
| Sources: tests | PASS | not_null, unique |
| Sources: `dbt source freshness` | PASS | |
| View materialization | PASS | Created and replaced |
| Table materialization | PASS | Created; rebuilt through the rename swap |
| Incremental, `append` | PASS | Second run appends only new rows (checked 4 → 5) |
| Incremental, `merge`, first build | PASS | |
| Incremental, `merge`, incremental run | **FAIL** | Fixed in opteryx-core, awaiting deploy |
| Tests: not_null, unique, singular | PASS | |
| Tests: accepted_values, relationships | **FAIL** | Fixed in opteryx-core, awaiting deploy |
| `dbt docs generate` | PARTIAL | Catalog written; views have no columns. Fixed in opteryx-core, awaiting deploy |
| Schema creation (`CREATE COLLECTION`) | PASS with workaround | `query-comment: {append: true}`. Fixed in opteryx-core, awaiting deploy |
| Incremental, `delete+insert`, first build | PASS | |
| Incremental, `delete+insert`, incremental run | PASS | Verified 2026-11-10 |
| Ephemeral models | **FAIL** | Fixed in opteryx-core, awaiting deploy |
| Snapshots (timestamp and check strategies) | **FAIL** | Issue 14 |
| Unit tests | **FAIL** | Was issue 15. Fixed in this adapter 2026-11-12 (`WHERE 1 = 0`); not re-run against opteryx.app |
| `--empty` | **FAIL** | Was issue 15. Fixed in this adapter 2026-11-12 (`WHERE 1 = 0`); not re-run against opteryx.app |
| Model contracts | **Refused** | The adapter raises (see above) |
| Pre/post hooks | PASS | Hook statements ran, checked in `hook_log` |
| `dbt show` | PASS | |
| `dbt run-operation` with `run_query` | PASS | |

## Issues found

| # | Issue | Class | Proposed fix |
|---|---|---|---|
| 10 | `ALTER TABLE x RENAME TO y` with a bare target is read as a move to another workspace. | Behaviour (documented) | None needed: the adapter always passes the qualified name. |
| 14 | `SELECT *, x` is refused by design ("`SELECT *` cannot coexist with additional columns"); `SELECT t.*, x` works. dbt's snapshot SQL uses `SELECT *, …`. | Opteryx dialect rule | Left as it is (ruled 2026-11-12). Lifting the engine's refusal is not enough: a bare star beside other columns expands computed columns twice. Snapshots stay unsupported unless the adapter overrides dbt's snapshot macros. |
| 15 | `WHERE false` is refused by design ("WHERE clause cannot be a bare literal"); `WHERE 1 = 0` works. dbt's `--empty` renders refs as `(SELECT * FROM x WHERE false LIMIT 0)`, and its schema-only subquery uses the same pattern. | Opteryx dialect rule | Fixed in this adapter 2026-11-12: `OpteryxRelation.render_limited` and `opteryx__get_empty_subquery_sql` render `WHERE 1 = 0`. The dialect rule is unchanged. |
