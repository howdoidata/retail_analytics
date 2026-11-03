{#- Use a model's custom schema as-is (`staging`, `intermediate`) instead of
    dbt's default `<target>_<custom>`; models without one land in `main`. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
