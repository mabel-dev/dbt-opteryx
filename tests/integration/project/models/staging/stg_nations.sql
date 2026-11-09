{{ config(materialized='view') }}
SELECT n_nationkey AS nation_key, n_name AS nation_name, n_regionkey AS region_key
FROM {{ source('tpch', 'nation') }}
