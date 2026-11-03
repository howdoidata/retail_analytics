-- One row per channel, signup cohort month, and milestone (long format): customers in the cohort who reached
-- the milestone, the share of the previous step that moved on, average days from the previous step, and the
-- cohort's simulated ad spend on the signup row. Milestones are 0 (signup) plus the `milestones` variable,
-- generated as rows here, so adding a milestone adds rows, never columns or queries. The grid is every channel
-- x every month from the first to the last month with a sign-up or spend x every milestone.

{%- set milestones = ([0] + var('milestones')) | unique | sort | list %}

with

customers as (

    select * from {{ ref('dim_customers') }}

),

channels as (

    select * from {{ ref('channels') }}

),

spend as (

    select * from {{ ref('int_channel_spend_daily') }}

),

milestone_list as (

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

-- Each customer at each milestone: the date they reached it and the date they reached the step before
-- (signup_date stands for milestone 0), both read from the same `milestone_dates` map.
customer_steps as (

    select
        customers.acquisition_channel as channel,
        cast(date_trunc('month', customers.signup_date) as date) as cohort_month,
        milestone_list.milestone,
        milestone_list.previous_milestone,
        case
            when milestone_list.milestone = 0 then customers.signup_date
            else customers.milestone_dates[milestone_list.milestone]
        end as reached_date,
        case
            when milestone_list.previous_milestone = 0 then customers.signup_date
            else customers.milestone_dates[milestone_list.previous_milestone]
        end as previous_date,
    from customers
    cross join milestone_list

),

reached_by_month as (

    select
        channel,
        cohort_month,
        milestone,
        count(reached_date) as customers_reached,
        avg(date_diff('day', previous_date, reached_date)) as avg_days_from_previous,
    from customer_steps
    group by
        channel,
        cohort_month,
        milestone

),

signups_by_month as (

    select distinct
        acquisition_channel as channel,
        cast(date_trunc('month', signup_date) as date) as cohort_month,
    from customers

),

spend_by_month as (

    select
        channel,
        cast(date_trunc('month', spend_date) as date) as cohort_month,
        sum(ad_spend) as ad_spend,
    from spend
    group by
        channel,
        date_trunc('month', spend_date)

),

active_months as (

    select cohort_month from signups_by_month
    union all
    select cohort_month from spend_by_month

),

months as (

    select
        cast(unnest(generate_series(
            min(cohort_month)::timestamp,
            max(cohort_month)::timestamp,
            interval 1 month
        )) as date) as cohort_month,
    from active_months

),

-- Channels outside the seed are kept, not dropped, so the relationships test fails on them.
grid_channels as (

    select channel from channels
    union
    select channel from signups_by_month
    union
    select channel from spend_by_month

),

grid as (

    select
        grid_channels.channel,
        months.cohort_month,
        milestone_list.milestone,
        milestone_list.previous_milestone,
    from grid_channels
    cross join months
    cross join milestone_list

),

filled as (

    select
        grid.channel,
        grid.cohort_month,
        grid.milestone,
        grid.previous_milestone,
        coalesce(reached_by_month.customers_reached, 0) as customers_reached,
        reached_by_month.avg_days_from_previous,
        coalesce(spend_by_month.ad_spend, 0) as month_ad_spend,
    from grid
    left join reached_by_month
        on grid.channel is not distinct from reached_by_month.channel
        and grid.cohort_month = reached_by_month.cohort_month
        and grid.milestone = reached_by_month.milestone
    left join spend_by_month
        on grid.channel is not distinct from spend_by_month.channel
        and grid.cohort_month = spend_by_month.cohort_month

),

stepped as (

    select
        *,
        lag(customers_reached) over (
            partition by channel, cohort_month
            order by milestone
        ) as previous_reached,
    from filled

),

final as (

    select
        channel,
        cohort_month,
        cast(milestone as integer) as milestone,
        cast(previous_milestone as integer) as previous_milestone,
        cast(customers_reached as integer) as customers_reached,
        cast(
            case
                when previous_milestone is not null and previous_reached != 0
                    then customers_reached / previous_reached
            end as decimal(18, 6)
        ) as step_rate,
        cast(
            case when previous_milestone is not null then avg_days_from_previous end as decimal(18, 2)
        ) as avg_days_from_previous,
        cast(case when milestone = 0 then month_ad_spend end as decimal(18, 2)) as ad_spend,
        true as is_simulated,
    from stepped

)

select * from final
