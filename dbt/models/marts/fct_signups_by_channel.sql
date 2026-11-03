-- One row per channel and quarter: sign-ups, the prior quarter's sign-ups and the change, the channel's
-- share of the quarter's sign-ups, simulated ad spend, and cost per signup. The grid is every channel x
-- every quarter from the first to the last quarter with a sign-up or spend, so quarters with nothing still
-- appear with 0, and the prior quarter is one `lag` over that grid (no query per quarter).

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

signups_by_quarter as (

    select
        acquisition_channel as channel,
        cast(date_trunc('quarter', signup_date) as date) as quarter,
        count(*) as signups,
    from customers
    group by
        acquisition_channel,
        date_trunc('quarter', signup_date)

),

spend_by_quarter as (

    select
        channel,
        cast(date_trunc('quarter', spend_date) as date) as quarter,
        sum(ad_spend) as ad_spend,
    from spend
    group by
        channel,
        date_trunc('quarter', spend_date)

),

active_quarters as (

    select quarter from signups_by_quarter
    union all
    select quarter from spend_by_quarter

),

quarters as (

    select
        cast(unnest(generate_series(
            min(quarter)::timestamp,
            max(quarter)::timestamp,
            interval 3 month
        )) as date) as quarter,
    from active_quarters

),

-- Channels outside the seed are kept, not dropped, so the relationships test fails on them.
grid_channels as (

    select channel from channels
    union
    select channel from signups_by_quarter
    union
    select channel from spend_by_quarter

),

grid as (

    select
        grid_channels.channel,
        quarters.quarter,
    from grid_channels
    cross join quarters

),

filled as (

    select
        grid.channel,
        grid.quarter,
        cast(coalesce(signups_by_quarter.signups, 0) as integer) as signups,
        cast(coalesce(spend_by_quarter.ad_spend, 0) as decimal(18, 2)) as ad_spend,
    from grid
    left join signups_by_quarter
        on grid.channel is not distinct from signups_by_quarter.channel
        and grid.quarter = signups_by_quarter.quarter
    left join spend_by_quarter
        on grid.channel is not distinct from spend_by_quarter.channel
        and grid.quarter = spend_by_quarter.quarter

),

compared as (

    select
        *,
        lag(signups) over (partition by channel order by quarter) as signups_prior_quarter,
        sum(signups) over (partition by quarter) as quarter_signups,
    from filled

),

final as (

    select
        channel,
        quarter,
        signups,
        cast(signups_prior_quarter as integer) as signups_prior_quarter,
        cast(
            case
                when signups_prior_quarter != 0
                    then (signups - signups_prior_quarter) / signups_prior_quarter
            end as decimal(18, 6)
        ) as signups_change,
        cast(
            case when quarter_signups != 0 then signups / quarter_signups end as decimal(18, 6)
        ) as share_of_signups,
        ad_spend,
        cast(
            case when signups != 0 and ad_spend != 0 then ad_spend / signups end as decimal(18, 2)
        ) as cost_per_signup,
        true as is_simulated,
    from compared

)

select * from final
