{% macro row_count(relation_name) %}
  {% set result = run_query("SELECT COUNT(*) AS n FROM " ~ ref(relation_name)) %}
  {{ log("row_count " ~ relation_name ~ " = " ~ result.columns[0].values()[0], info=True) }}
{% endmacro %}
