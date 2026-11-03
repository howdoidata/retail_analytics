{#- Grain test for a multi-column key: fails on every combination of `columns` that appears more than
    once. Built-in `unique` takes one column, and the project uses no packages. -#}
{% test unique_combination(model, columns) %}

select
    {{ columns | join(',\n    ') }},
    count(*) as rows_with_key,
from {{ model }}
group by
    {{ columns | join(',\n    ') }}
having count(*) > 1

{% endtest %}
