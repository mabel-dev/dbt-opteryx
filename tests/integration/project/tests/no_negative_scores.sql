SELECT id FROM {{ ref('stg_customers') }} WHERE score < 0
