-- The grid is complete: rows = channels in the seed x months from the first to the last, contiguous, x
-- milestones (0 plus the `milestones` variable, deduplicated), each previous_milestone the step before.

{%- set milestones = ([0] + var('milestones')) | unique | sort | list %}

with

funnel as (

    select * from {{ ref('fct_visit_funnel_by_channel') }}

),

channels as (

    select count(*) as channels from {{ ref('channels') }}

),

span as (

    select
        count(*) as grid_rows,
        count(distinct cohort_month) as months,
        coalesce(date_diff('month', min(cohort_month), max(cohort_month)) + 1, 0) as months_in_span,
        count(distinct milestone) as milestones,
    from funnel

),

expected_steps as (

    select
        milestone,
        lag(milestone) over (order by milestone) as previous_milestone,
    from (
        values
        {%- for milestone in milestones %}
            ({{ milestone }}){{ ',' if not loop.last }}
        {%- endfor %}
    ) as listed (milestone)

),

wrong_steps as (

    select count(*) as wrong_steps
    from funnel
    left join expected_steps
        on funnel.milestone = expected_steps.milestone
    where expected_steps.milestone is null
        or funnel.previous_milestone is distinct from expected_steps.previous_milestone

)

select
    span.grid_rows,
    span.months,
    span.months_in_span,
    span.milestones,
    channels.channels,
    wrong_steps.wrong_steps,
from span
cross join channels
cross join wrong_steps
where span.months != span.months_in_span
    or span.milestones != {{ milestones | length }}
    or span.grid_rows != channels.channels * span.months_in_span * {{ milestones | length }}
    or wrong_steps.wrong_steps != 0
