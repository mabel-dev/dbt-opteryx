{{ config(
    materialized='table',
    pre_hook="CREATE TABLE IF NOT EXISTS {{ this.database }}.{{ this.schema }}.hook_log (event VARCHAR)",
    post_hook="INSERT INTO {{ this.database }}.{{ this.schema }}.hook_log (event) VALUES ('built {{ this.identifier }}')"
) }}
SELECT id, name FROM {{ ref('customers') }}
