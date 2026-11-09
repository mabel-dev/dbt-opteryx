{# database = workspace, schema = collection, identifier = dataset #}

{% macro opteryx__get_binding_char() %}?{% endmacro %}

{% macro opteryx__current_timestamp() %}now(){% endmacro %}

{% macro opteryx__create_schema(relation) -%}
  {% call statement('create_schema') -%}
    CREATE COLLECTION IF NOT EXISTS {{ relation.without_identifier() }}
  {%- endcall %}
{% endmacro %}

{% macro opteryx__list_schemas(database) -%}
  {% call statement('list_schemas', fetch_result=True, auto_begin=False) %}
    SELECT schema_name FROM {{ database }}.information_schema.schemata
  {% endcall %}
  {{ return(load_result('list_schemas').table) }}
{% endmacro %}

{% macro opteryx__check_schema_exists(information_schema, schema) -%}
  {% call statement('check_schema_exists', fetch_result=True, auto_begin=False) -%}
    SELECT COUNT(*) FROM {{ information_schema.database }}.information_schema.schemata
    WHERE schema_name = '{{ schema }}'
  {%- endcall %}
  {{ return(load_result('check_schema_exists').table) }}
{% endmacro %}

{% macro opteryx__list_relations_without_caching(schema_relation) %}
  {% call statement('list_relations_without_caching', fetch_result=True) -%}
    SELECT
      table_catalog AS database,
      table_name AS name,
      table_schema AS schema,
      CASE WHEN table_type = 'VIEW' THEN 'view' ELSE 'table' END AS type
    FROM {{ schema_relation.database }}.information_schema.tables
    WHERE table_schema = '{{ schema_relation.schema }}'
  {%- endcall %}
  {{ return(load_result('list_relations_without_caching').table) }}
{% endmacro %}

{% macro opteryx__get_columns_in_relation(relation) -%}
  {% call statement('get_columns_in_relation', fetch_result=True) %}
    SELECT
      column_name,
      data_type,
      NULL AS character_maximum_length,
      NULL AS numeric_precision,
      NULL AS numeric_scale
    FROM {{ relation.database }}.information_schema.columns
    WHERE table_schema = '{{ relation.schema }}'
      AND table_name = '{{ relation.identifier }}'
    ORDER BY ordinal_position
  {% endcall %}
  {% set table = load_result('get_columns_in_relation').table %}
  {{ return(sql_convert_columns_in_relation(table)) }}
{% endmacro %}

{% macro opteryx__create_table_as(temporary, relation, sql) -%}
  {#- Opteryx has no temporary tables; dbt drops its intermediates itself. -#}
  {%- if config.get('contract').enforced -%}
    {{ exceptions.raise_compiler_error("dbt-opteryx does not enforce model contracts; remove `contract: {enforced: true}` from " ~ relation) }}
  {%- endif -%}
  CREATE TABLE {{ relation }} AS {{ sql }}
{%- endmacro %}

{% macro opteryx__create_view_as(relation, sql) -%}
  CREATE OR REPLACE VIEW {{ relation }} AS {{ sql }}
{%- endmacro %}

{% macro opteryx__drop_relation(relation) -%}
  {% call statement('drop_relation', auto_begin=False) -%}
    DROP {{ relation.type }} IF EXISTS {{ relation }}
  {%- endcall %}
{% endmacro %}

{% macro opteryx__rename_relation(from_relation, to_relation) -%}
  {#- Opteryx requires the fully qualified target name. -#}
  {% call statement('rename_relation') -%}
    ALTER {{ from_relation.type }} {{ from_relation }} RENAME TO {{ to_relation }}
  {%- endcall %}
{% endmacro %}
