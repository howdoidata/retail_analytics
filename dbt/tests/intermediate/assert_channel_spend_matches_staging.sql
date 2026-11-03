-- Summing campaigns into days keeps every dollar: total spend in int_channel_spend_daily equals the total
-- in stg_ad_spend.

with

staging_spend as (

    select coalesce(sum(spend), 0) as spend from {{ ref('stg_ad_spend') }}

),

daily_spend as (

    select coalesce(sum(ad_spend), 0) as spend from {{ ref('int_channel_spend_daily') }}

)

select
    staging_spend.spend as staging_total,
    daily_spend.spend as daily_total,
from staging_spend
cross join daily_spend
where staging_spend.spend != daily_spend.spend
