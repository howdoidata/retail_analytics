-- Within each channel and cohort quarter, cohort_size is the same on every offset row, and active_customers
-- never exceeds it.

with

sized as (

    select
        channel,
        cohort_quarter,
        quarters_since_signup,
        cohort_size,
        active_customers,
        min(cohort_size) over (partition by channel, cohort_quarter) as min_size,
        max(cohort_size) over (partition by channel, cohort_quarter) as max_size,
    from {{ ref('fct_customer_cohorts') }}

)

select * from sized
where active_customers > cohort_size
    or min_size != max_size
