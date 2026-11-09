{{ config(materialized='table') }}
SELECT id, name, country FROM {{ ref('int_active_customers') }}
