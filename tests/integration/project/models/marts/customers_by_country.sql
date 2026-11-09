{{ config(materialized='table') }}
SELECT country, COUNT(*) AS customers, AVG(score) AS avg_score
FROM {{ ref('stg_customers') }}
GROUP BY country
