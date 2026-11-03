-- Step rates are shares, from 0 to 1.

select
    channel,
    cohort_month,
    milestone,
    step_rate,
from {{ ref('fct_visit_funnel_by_channel') }}
where step_rate < 0 or step_rate > 1
