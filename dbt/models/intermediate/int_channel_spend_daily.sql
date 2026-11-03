-- One row per channel and day of simulated ad spend, summed over campaigns. The marts roll it up to their
-- own period (quarter, month), so one spend model serves every period.

with

ad_spend as (

    select * from {{ ref('stg_ad_spend') }}

),

daily as (

    select
        channel,
        date as spend_date,
        cast(sum(spend) as decimal(18, 2)) as ad_spend,
    from ad_spend
    group by
        channel,
        date

),

final as (

    select * from daily

)

select * from final
