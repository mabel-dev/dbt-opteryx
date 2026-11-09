{#-
  Seed rows are rendered as typed literals, not bind parameters: parameters reach
  Opteryx as JSON values, JSON has no DATE/TIMESTAMP, and INSERT will not coerce a
  VARCHAR into a typed column.
-#}
{% macro opteryx__load_csv_rows(model, agate_table) %}
  {% set column_override = model['config'].get('column_types', {}) %}
  {% set types = [] %}
  {% for col_name in agate_table.column_names %}
    {% do types.append(column_override.get(col_name, adapter.convert_type(agate_table, loop.index0))) %}
  {% endfor %}
  {% set cols_sql = get_seed_column_quoted_csv(model, agate_table.column_names) %}
  {% set statements = [] %}

  {% for chunk in agate_table.rows | batch(get_batch_size()) %}
    {% set sql %}
      INSERT INTO {{ this.render() }} ({{ cols_sql }}) VALUES
      {% for row in chunk -%}
        ({%- for value in row -%}
          {%- if value is none -%}NULL{%- else -%}CAST('{{ (value | string) | replace("'", "''") }}' AS {{ types[loop.index0] }}){%- endif -%}
          {%- if not loop.last %}, {% endif -%}
        {%- endfor -%})
        {%- if not loop.last %},{% endif %}
      {% endfor %}
    {% endset %}
    {% do adapter.add_query(sql, abridge_sql_log=True) %}
    {% if loop.index0 == 0 %}
      {% do statements.append(sql) %}
    {% endif %}
  {% endfor %}

  {{ return(statements[0]) }}
{% endmacro %}
