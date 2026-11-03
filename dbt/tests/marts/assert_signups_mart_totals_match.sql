-- No sign-up or spend is lost or duplicated by the grid joins: the mart's sign-ups equal the customers in
-- dim_customers, and its spend equals the total in int_channel_spend_daily.

with

mart as (

    select
        coalesce(sum(signups), 0) as signups,
        coalesce(sum(ad_spend), 0) as ad_spend,
    from {{ ref('fct_signups_by_channel') }}

),

customers as (

    select count(*) as signups from {{ ref('dim_customers') }}

),

spend as (

    select coalesce(sum(ad_spend), 0) as ad_spend from {{ ref('int_channel_spend_daily') }}

)

select
    mart.signups as mart_signups,
    customers.signups as customer_signups,
    mart.ad_spend as mart_ad_spend,
    spend.ad_spend as daily_ad_spend,
from mart
cross join customers
cross join spend
where mart.signups != customers.signups
    or mart.ad_spend != spend.ad_spend
