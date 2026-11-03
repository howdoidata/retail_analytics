-- The cohort average avg_days_from_previous is never negative on any row.

select
    channel,
    cohort_month,
    milestone,
    avg_days_from_previous,
from {{ ref('fct_visit_funnel_by_channel') }}
where avg_days_from_previous < 0
