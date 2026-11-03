{#- M2: one spelling per email address: surrounding whitespace trimmed, lowercased, empty as null.
    Used for customers.email and marketing_touches.customer_email so the two match. -#}
{% macro normalize_email(column) -%}
    nullif(lower(trim({{ column }})), '')
{%- endmacro %}
