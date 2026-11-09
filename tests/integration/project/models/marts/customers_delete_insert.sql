{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='id') }}
SELECT id, name, updated_at FROM {{ ref('customers') }}
{% if is_incremental() %}
WHERE updated_at >= (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
