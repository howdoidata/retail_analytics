-- The signup row (milestone 0) and only it has a null previous_milestone and a non-null ad_spend, and its
-- step_rate and avg_days_from_previous are null. On every other row, step_rate is null exactly when nobody
-- reached the previous step, and avg_days_from_previous exactly when nobody reached this one.

with

stepped as (

    select
        *,
        lag(customers_reached) over (
            partition by channel, cohort_month
            order by milestone
        ) as previous_reached,
    from {{ ref('fct_visit_funnel_by_channel') }}

)

select
    channel,
    cohort_month,
    milestone,
    previous_milestone,
    step_rate,
    avg_days_from_previous,
    ad_spend,
from stepped
where (milestone = 0) != (previous_milestone is null)
    or (milestone = 0) != (ad_spend is not null)
    or (milestone = 0 and (step_rate is not null or avg_days_from_previous is not null))
    or (milestone != 0 and (step_rate is null) != (previous_reached = 0))
    or (milestone != 0 and (avg_days_from_previous is null) != (customers_reached = 0))
