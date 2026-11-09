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

Put this in `dbt_project.yml` until the leading-comment issue below is fixed:

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
  parameters: parameters reach Opteryx as JSON, which has no DATE or TIMESTAMP.
- **Incremental strategies:** `append`, `merge` and `delete+insert`.
- **Model contracts are refused**, with an error naming the model: the adapter does
  not enforce them yet, and ignoring one silently would claim a guarantee it does not keep.
- **Queries cannot be cancelled** from dbt.

## Integration tests

`tests/integration/project` is a dbt project covering seeds, sources (including
freshness), view, table, ephemeral and incremental models (all three strategies),
snapshots, hooks, contracts, generic, singular and unit tests, `show`,
`run-operation`, `--empty` and docs generation. Run it against opteryx.app:

```bash
OPTERYX_USER=… OPTERYX_TOKEN=… tests/integration/run.sh
```

It writes into `personal.$OPTERYX_USER` (override with `OPTERYX_WORKSPACE` /
`OPTERYX_COLLECTION`). CI runs it on push (`.github/workflows/integration.yaml`),
reading `OPTERYX_USER` / `OPTERYX_TOKEN` from repository secrets.

Offline checks (no connection) run with `python -m pytest tests/unit`.

## CI

| Workflow | Runs on | Does |
|---|---|---|
| `regression-tests.yaml` | push | `tests/unit` on Python 3.10–3.14 × dbt-core 1.10 (floor) and latest |
| `integration.yaml` | push | `tests/integration/run.sh` against opteryx.app |
| `semgrep_scan.yaml` | push | Semgrep scan, findings uploaded to `opteryx.ops.sast_findings` |
| `release.yaml` | `v*` tag | Builds and publishes to PyPI by trusted publishing |

Repository secrets: `OPTERYX_USER`, `OPTERYX_TOKEN` (integration), `UPLOAD_CLIENT`,
`UPLOAD_TOKEN` (Semgrep upload).

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
| Seeds, reload over an existing table | **FAIL (silent)** | Reports OK but doubles the rows: TRUNCATE is a no-op (issue 1) |
| Seeds, `--full-refresh` | PASS | Drops and recreates |
| Sources: `source()` reads | PASS | `samples.tpch_sf001.nation` |
| Sources: tests | PASS | not_null, unique |
| Sources: `dbt source freshness` | PASS | |
| View materialization | PASS | Created and replaced |
| Table materialization | PASS | Created; rebuilt through the rename swap |
| Incremental, `append` | PASS | Second run appends only new rows (checked 4 → 5) |
| Incremental, `merge`, first build | PASS | |
| Incremental, `merge`, incremental run | **FAIL** | Issue 3 |
| Tests: not_null, unique, singular | PASS | |
| Tests: accepted_values, relationships | **FAIL** | Issue 4 |
| `dbt docs generate` | PARTIAL | Catalog written; views have no columns (issue 5) |
| Schema creation (`CREATE COLLECTION`) | PASS with workaround | Issue 2 |
| Incremental, `delete+insert`, first build | PASS | |
| Incremental, `delete+insert`, incremental run | **FAIL** | Issues 11 and 12 |
| Ephemeral models | **FAIL** | Issue 13 |
| Snapshots (timestamp and check strategies) | **FAIL** | Issue 14; would then hit issue 3 |
| Unit tests | **FAIL** | Issue 5: fixtures need the input view's columns |
| `--empty` | **FAIL** | Issue 15 |
| Model contracts | **Refused** | The adapter raises (see above) |
| Pre/post hooks | PASS | Hook statements ran, checked in `hook_log` |
| `dbt show` | PASS | |
| `dbt run-operation` with `run_query` | PASS | |

## Issues found

| # | Issue | Class | Proposed fix |
|---|---|---|---|
| 1 | `TRUNCATE TABLE` reports OK and removes nothing. `OpteryxConnector.truncate_relation` calls `Dataset.truncate()`, whose default `commit_truncation=False` never moves `current-snapshot-id`. | Opteryx correctness bug | **Fixed in opteryx-core (2026-11-09, not yet released or deployed):** the connector now passes `commit_truncation=True`. Re-run the matrix after deploy. |
| 2 | `CREATE/DROP COLLECTION` and `ALTER/DROP WORKSPACE` fail to parse after a leading comment. dbt puts a comment in front of every statement. | Opteryx SQL gap | Have the `^\s*` anchors in `opteryx/planner/sql_rewriter/__init__.py:240-251` skip leading comments. Docs workaround: `query-comment: {append: true}`. |
| 3 | `MERGE … WHEN NOT MATCHED THEN INSERT (…) VALUES ("id", …)` raises "Column id is ambiguous". Only the source is in scope there; qualified `S."id"` works. | Opteryx SQL gap | Bind WHEN NOT MATCHED value expressions against the source relation only. |
| 4 | A CTE inside a derived table is not found: `SELECT … FROM (WITH a AS (…) SELECT * FROM a) t` gives "Dataset `a` cannot be found". dbt wraps every test in such a subquery. | Opteryx SQL gap | Scope CTEs declared inside a subquery to that subquery. |
| 5 | `information_schema.columns` has no rows for views, so dbt cannot see view columns. | Opteryx SQL gap | List view columns there as well; it currently iterates `list_datasets()` only. |
| 6 | `personal.information_schema.schemata` is empty although `personal.<user>` exists. dbt then always issues `CREATE COLLECTION IF NOT EXISTS`, which succeeds. | Opteryx catalog gap (not blocking) | List the caller's personal collection. |
| 7 | CAST refuses `DOUBLE`, `BIGINT` and `TEXT` ("not a type CAST can produce") although `reference/types.json` lists them as accepted spellings. dbt's default seed types are `text` / `float8`. | Opteryx SQL gap | Accept the listed spellings in CAST. The adapter maps seed types itself meanwhile. |
| 8 | INSERT type errors print the enum repr, e.g. "target LogicalCategory.FLOAT". | Opteryx message bug | Render the type name. |
| 9 | Bind parameters of type `Decimal`, `date` or `datetime` fail with "not JSON serializable" in the DBAPI. | Adapter/protocol gap (opteryx-sqlalchemy) | Encode them in `_submit_statement`. Even then, the server will not coerce a string into DATE/TIMESTAMP, so this adapter's seeds use literals. |
| 10 | `ALTER TABLE x RENAME TO y` with a bare target is read as a move to another workspace. | Behaviour (documented) | None needed: the adapter always passes the qualified name. |
| 11 | `WHERE (id) IN (SELECT …)` with one parenthesised column fails: "A correlated EXISTS/IN subquery correlates on `(id)`…". Without the parentheses it works. dbt's delete+insert always parenthesises. | Opteryx SQL gap | Treat a one-element parenthesised expression as the expression itself. |
| 12 | **INSERT fails after a DELETE that removed every row** of the table's files: "concat: all inputs must share one type for 'column_uncompressed_sizes_in_bytes' - found INT64, ARRAY". Root cause is in rugo: a zero-row `array<…>` column reads back as INT64. The delete-all writes a manifest with one zero-row row group, INSERT appends a row group to it, and `read_manifest_columns` cannot combine the two. Three-line reproducer: write an empty ARRAY vector with `rugo.parquet.write_parquet`; `read_parquet` returns it as INT64. Not dbt-specific. | Opteryx correctness bug (rugo reader) | **Fixed in opteryx-core (2026-11-09, not yet released or deployed):** the reader routes list columns on the schema's `max_rep_level`, not on whether repetition levels were decoded. Manifests already written this way need no rewrite; they read correctly once the fix is deployed. |
| 13 | `CREATE TABLE … AS WITH a AS (…) SELECT … FROM a` gives "Dataset `a` cannot be found". The same query without CREATE works. dbt inlines ephemeral models this way. | Opteryx SQL gap | Resolve CTEs in a CTAS body. |
| 14 | `SELECT *, x` is refused by design ("`SELECT *` cannot coexist with additional columns"); `SELECT t.*, x` works. dbt's snapshot SQL uses `SELECT *, …`. | Opteryx dialect rule | Either allow `*` with other columns, or override dbt's snapshot macros in the adapter to qualify the star. Architect's call. |
| 15 | `WHERE false` is refused by design ("WHERE clause cannot be a bare literal"); `WHERE 1 = 0` works. dbt's `--empty` renders refs as `(SELECT * FROM x WHERE false LIMIT 0)`, and contract enforcement uses the same pattern. | Opteryx dialect rule | Either accept a bare boolean literal, or override the relation's limited render in the adapter. Architect's call. |
