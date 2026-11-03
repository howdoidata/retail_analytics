-- Active rates are shares, from 0 to 1, and each ratio is null exactly when its denominator is 0:
-- active_rate (cohort_size), visits_per_active_customer (active_customers), average_order (visits).

select
    channel,
    cohort_quarter,
    quarters_since_signup,
    cohort_size,
    active_customers,
    visits,
    active_rate,
    visits_per_active_customer,
    average_order,
from {{ ref('fct_customer_cohorts') }}
where active_rate < 0
    or active_rate > 1
    or (active_rate is null) != (cohort_size = 0)
    or (visits_per_active_customer is null) != (active_customers = 0)
    or (average_order is null) != (visits = 0)
