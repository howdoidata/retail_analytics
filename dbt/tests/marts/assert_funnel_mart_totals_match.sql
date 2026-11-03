-- No customer or dollar is lost or duplicated by the grid joins: signup-row customers_reached sums to the
-- customers in dim_customers, and ad_spend sums to the total in int_channel_spend_daily.

with

mart as (

    select
        coalesce(sum(customers_reached) filter (where milestone = 0), 0) as customers,
        coalesce(sum(ad_spend), 0) as ad_spend,
    from {{ ref('fct_visit_funnel_by_channel') }}

),

customers as (

    select count(*) as customers from {{ ref('dim_customers') }}

),

spend as (

    select coalesce(sum(ad_spend), 0) as ad_spend from {{ ref('int_channel_spend_daily') }}

)

select
    mart.customers as mart_customers,
    customers.customers as dim_customers,
    mart.ad_spend as mart_ad_spend,
    spend.ad_spend as daily_ad_spend,
from mart
cross join customers
cross join spend
where mart.customers != customers.customers
    or mart.ad_spend != spend.ad_spend
