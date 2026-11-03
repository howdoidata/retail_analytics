{#- M3: parse a source date in either of its two forms (`YYYY-MM-DD`, `MM/DD/YYYY`) to a `date`.
    Anything else gives null, which the not_null tests catch. -#}
{% macro parse_date(column) -%}
    coalesce(
        case
            when regexp_full_match({{ column }}, '\d{4}-\d{2}-\d{2}')
                then try_strptime({{ column }}, '%Y-%m-%d')
        end,
        case
            when regexp_full_match({{ column }}, '\d{2}/\d{2}/\d{4}')
                then try_strptime({{ column }}, '%m/%d/%Y')
        end
    )::date
{%- endmacro %}
