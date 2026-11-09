{{ config(materialized='ephemeral') }}
SELECT id, name, country FROM {{ ref('stg_customers') }} WHERE active
