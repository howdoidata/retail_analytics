-- One row per channel, signup quarter, and quarters since signup (long format): the cohort's size, the
-- customers still visiting in that later quarter, their visits, and what they spent. Offsets 0 (the signup
-- quarter) to the `cohort_horizon_quarters` variable are generated as rows here, so changing the horizon adds
-- or removes rows, never columns or queries. The grid is every channel x every quarter from the first to the
-- last quarter with a sign-up x every offset whose calendar quarter is not after the quarter the data ends
-- (the latest signup or visit date).

{%- set horizon = var('cohort_horizon_quarters') | int %}

with

customers as (

    select * from {{ ref('dim_customers') }}

),

visits as (

    select * from {{ ref('int_customer_visits') }}

),

channels as (

    select * from {{ ref('channels') }}

),

offset_list as (

    select unnest(generate_series(0, {{ horizon }})) as quarters_since_signup

),

cohort_customers as (

    select
        customer_id,
        acquisition_channel as channel,
        cast(date_trunc('quarter', signup_date) as date) as cohort_quarter,
    from customers

),

cohort_sizes as (

    select
        channel,
        cohort_quarter,
        count(*) as cohort_size,
    from cohort_customers
    group by
        channel,
        cohort_quarter

),

-- Each visit placed in its cohort at its calendar-quarter offset from the signup quarter.
visit_offsets as (

    select
        cohort_customers.channel,
        cohort_customers.cohort_quarter,
        cohort_customers.customer_id,
        date_diff(
            'quarter', cohort_customers.cohort_quarter, date_trunc('quarter', visits.visit_date)
        ) as quarters_since_signup,
        visits.order_total,
    from visits
    inner join cohort_customers
        on visits.customer_id = cohort_customers.customer_id

),

activity as (

    select
        channel,
        cohort_quarter,
        quarters_since_signup,
        count(distinct customer_id) as active_customers,
        count(*) as visits,
        sum(order_total) as revenue,
    from visit_offsets
    where quarters_since_signup <= {{ horizon }}
    group by
        channel,
        cohort_quarter,
        quarters_since_signup

),

data_end as (

    select cast(date_trunc('quarter', max(data_date)) as date) as data_end_quarter,
    from (
        select signup_date as data_date from customers
        union all
        select visit_date as data_date from visits
    ) as dated

),

quarters as (

    select
        cast(unnest(generate_series(
            min(cohort_quarter)::timestamp,
            max(cohort_quarter)::timestamp,
            interval 3 month
        )) as date) as cohort_quarter,
    from cohort_customers

),

-- Channels outside the seed are kept, not dropped, so the relationships test fails on them.
grid_channels as (

    select channel from channels
    union
    select channel from cohort_customers

),

grid as (

    select
        grid_channels.channel,
        quarters.cohort_quarter,
        offset_list.quarters_since_signup,
    from grid_channels
    cross join quarters
    cross join offset_list
    cross join data_end
    where date_diff('quarter', quarters.cohort_quarter, data_end.data_end_quarter)
        >= offset_list.quarters_since_signup

),

filled as (

    select
        grid.channel,
        grid.cohort_quarter,
        grid.quarters_since_signup,
        coalesce(cohort_sizes.cohort_size, 0) as cohort_size,
        coalesce(activity.active_customers, 0) as active_customers,
        coalesce(activity.visits, 0) as visits,
        coalesce(activity.revenue, 0) as revenue,
    from grid
    left join cohort_sizes
        on grid.channel is not distinct from cohort_sizes.channel
        and grid.cohort_quarter = cohort_sizes.cohort_quarter
    left join activity
        on grid.channel is not distinct from activity.channel
        and grid.cohort_quarter = activity.cohort_quarter
        and grid.quarters_since_signup = activity.quarters_since_signup

),

final as (

    select
        channel,
        cohort_quarter,
        cast(quarters_since_signup as integer) as quarters_since_signup,
        cast(cohort_size as integer) as cohort_size,
        cast(active_customers as integer) as active_customers,
        cast(
            case when cohort_size != 0 then active_customers / cohort_size end as decimal(18, 6)
        ) as active_rate,
        cast(visits as integer) as visits,
        cast(
            case when active_customers != 0 then visits / active_customers end as decimal(18, 4)
        ) as visits_per_active_customer,
        cast(revenue as decimal(18, 2)) as revenue,
        cast(case when visits != 0 then revenue / visits end as decimal(18, 2)) as average_order,
        true as is_simulated,
    from filled

)

select * from final
