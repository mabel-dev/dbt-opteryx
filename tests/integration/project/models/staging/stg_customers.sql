{{ config(materialized='view') }}
SELECT id, name, country, signup_date, score, active
FROM {{ ref('customers') }}
