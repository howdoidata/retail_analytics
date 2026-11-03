-- Every configured milestone is a key of milestone_dates, and the dates never decrease as the milestone
-- rises: a later milestone is null when an earlier one is, and never dated before it.

{%- set milestones = var('milestones') | unique | sort | list %}

select
    customer_id,
    milestone_dates,
from {{ ref('dim_customers') }}
where map_keys(milestone_dates) != [{% for milestone in milestones %}{{ milestone }}{{ ', ' if not loop.last }}{% endfor %}]
{%- for milestone in milestones[1:] %}
{%- set previous = milestones[loop.index0] %}
    or (milestone_dates[{{ previous }}] is null and milestone_dates[{{ milestone }}] is not null)
    or milestone_dates[{{ milestone }}] < milestone_dates[{{ previous }}]
{%- endfor %}
