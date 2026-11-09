{{ config(materialized='table') }}
SELECT region_key, COUNT(*) AS nations
FROM {{ ref('stg_nations') }}
GROUP BY region_key
