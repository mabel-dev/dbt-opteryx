#!/usr/bin/env bash
# Runs the dbt feature matrix against opteryx.app.
# Needs OPTERYX_USER and OPTERYX_TOKEN; writes into personal.<OPTERYX_USER> unless
# OPTERYX_WORKSPACE / OPTERYX_COLLECTION say otherwise.
set -euo pipefail
cd "$(dirname "$0")/project"
export DBT_SEND_ANONYMOUS_USAGE_STATS=false
dbt() { command dbt "$@" --project-dir . --profiles-dir .; }

dbt debug
dbt seed --full-refresh
dbt run --full-refresh
dbt seed            # re-seed over an existing table
dbt run             # second pass: table swap + incremental paths
dbt test
dbt snapshot
dbt snapshot        # second pass: change detection
dbt source freshness
dbt show --select customers_by_country
dbt run-operation row_count --args '{relation_name: customers}'
dbt run --empty
dbt docs generate
