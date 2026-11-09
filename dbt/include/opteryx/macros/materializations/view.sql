{#- Opteryx has CREATE OR REPLACE VIEW and no view rename, so skip dbt's tmp/rename swap. -#}
{% materialization view, adapter='opteryx' -%}
  {{ return(create_or_replace_view()) }}
{%- endmaterialization %}
