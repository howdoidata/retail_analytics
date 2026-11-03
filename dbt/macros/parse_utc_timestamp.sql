{#- M3: parse a source timestamp in any of its four forms to a naive `timestamp` in UTC.

    Forms (data/raw/README.md): ISO 8601 with `Z`, ISO 8601 with an offset, `YYYY-MM-DD HH:MM:SS`,
    and `MM/DD/YYYY HH:MM`. Values without an offset are UTC, so `+00:00` is appended before parsing.
    Each form is matched exactly first; anything else (or an impossible date) gives null, which the
    not_null tests catch. Going through epoch microseconds keeps the result in UTC whatever the
    session time zone is. -#}
{% macro parse_utc_timestamp(column) -%}
    make_timestamp(epoch_us(coalesce(
        case
            when regexp_full_match({{ column }}, '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})')
                then try_strptime(replace({{ column }}, 'Z', '+00:00'), '%Y-%m-%dT%H:%M:%S%z')
        end,
        case
            when regexp_full_match({{ column }}, '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
                then try_strptime({{ column }} || '+00:00', '%Y-%m-%d %H:%M:%S%z')
        end,
        case
            when regexp_full_match({{ column }}, '\d{2}/\d{2}/\d{4} \d{2}:\d{2}')
                then try_strptime({{ column }} || '+00:00', '%m/%d/%Y %H:%M%z')
        end
    )))
{%- endmacro %}
