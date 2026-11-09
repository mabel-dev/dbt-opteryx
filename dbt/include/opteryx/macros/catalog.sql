{% macro opteryx__get_catalog(information_schema, schemas) -%}
  {% set query %}
    SELECT
      t.table_catalog AS table_database,
      t.table_schema AS table_schema,
      t.table_name AS table_name,
      CASE WHEN t.table_type = 'VIEW' THEN 'VIEW' ELSE 'BASE TABLE' END AS table_type,
      NULL AS table_comment,
      c.column_name AS column_name,
      c.ordinal_position AS column_index,
      c.data_type AS column_type,
      NULL AS column_comment,
      NULL AS table_owner
    FROM {{ information_schema.database }}.information_schema.tables AS t
    INNER JOIN {{ information_schema.database }}.information_schema.columns AS c
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE t.table_schema IN (
      {%- for schema in schemas -%}'{{ schema }}'{%- if not loop.last %}, {% endif -%}{%- endfor -%}
    )
    ORDER BY t.table_schema, t.table_name, c.ordinal_position
  {% endset %}
  {{ return(run_query(query)) }}
{%- endmacro %}
