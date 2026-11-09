{{ config(materialized='incremental', incremental_strategy='append') }}
SELECT id, updated_at
FROM {{ source('loaded', 'customers') }}
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
