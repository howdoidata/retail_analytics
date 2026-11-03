-- No row is for a quarter after the data ends: cohort_quarter plus quarters_since_signup is never after the
-- quarter of the latest signup or visit date in dim_customers and int_customer_visits.

with

data_end as (

    select date_trunc('quarter', max(data_date)) as data_end_quarter,
    from (
        select signup_date as data_date from {{ ref('dim_customers') }}
        union all
        select visit_date as data_date from {{ ref('int_customer_visits') }}
    ) as dated

)

select
    cohorts.channel,
    cohorts.cohort_quarter,
    cohorts.quarters_since_signup,
    data_end.data_end_quarter,
from {{ ref('fct_customer_cohorts') }} as cohorts
cross join data_end
where cohorts.cohort_quarter + to_months(3 * cohorts.quarters_since_signup) > data_end.data_end_quarter
