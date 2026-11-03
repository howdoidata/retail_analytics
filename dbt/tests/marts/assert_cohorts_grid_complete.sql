-- The grid is complete and has nothing extra: its keys are exactly the channels in the seed x every quarter
-- from the first to the last signup quarter x offsets 0 to `cohort_horizon_quarters` whose quarter is not
-- after the data-end quarter. Returns each missing or extra key.

{%- set horizon = var('cohort_horizon_quarters') | int %}

with

customers as (

    select * from {{ ref('dim_customers') }}

),

data_end as (

    select date_trunc('quarter', max(data_date)) as data_end_quarter,
    from (
        select signup_date as data_date from customers
        union all
        select visit_date as data_date from {{ ref('int_customer_visits') }}
    ) as dated

),

quarters as (

    select
        cast(unnest(generate_series(
            min(date_trunc('quarter', signup_date))::timestamp,
            max(date_trunc('quarter', signup_date))::timestamp,
            interval 3 month
        )) as date) as cohort_quarter,
    from customers

),

expected as (

    select
        channels.channel,
        quarters.cohort_quarter,
        offsets.quarters_since_signup,
    from {{ ref('channels') }} as channels
    cross join quarters
    cross join (select unnest(range(0, {{ horizon + 1 }})) as quarters_since_signup) as offsets
    cross join data_end
    where quarters.cohort_quarter + to_months(3 * offsets.quarters_since_signup) <= data_end.data_end_quarter

),

actual as (

    select
        channel,
        cohort_quarter,
        quarters_since_signup,
    from {{ ref('fct_customer_cohorts') }}

),

missing as (

    select *, 'missing' as problem from (select * from expected except all select * from actual)

),

extra as (

    select *, 'extra' as problem from (select * from actual except all select * from expected)

)

select * from missing
union all
select * from extra
