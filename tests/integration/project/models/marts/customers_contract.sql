{{ config(materialized='table') }}
SELECT id, name, score FROM {{ ref('customers') }}
