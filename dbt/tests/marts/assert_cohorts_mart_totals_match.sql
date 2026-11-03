-- No customer, visit, or dollar is lost or duplicated by the grid joins: offset-0 cohort_size sums to the
-- customers in dim_customers, and visits and revenue sum to the visits in int_customer_visits (and their
-- order totals) up to `cohort_horizon_quarters` quarters after the signup quarter.

{%- set horizon = var('cohort_horizon_quarters') | int %}

with

mart as (

    select
        coalesce(sum(cohort_size) filter (where quarters_since_signup = 0), 0) as customers,
        coalesce(sum(visits), 0) as visits,
        coalesce(sum(revenue), 0) as revenue,
    from {{ ref('fct_customer_cohorts') }}

),

customers as (

    select count(*) as customers from {{ ref('dim_customers') }}

),

visits as (

    select
        count(*) as visits,
        coalesce(sum(visits.order_total), 0) as revenue,
    from {{ ref('int_customer_visits') }} as visits
    inner join {{ ref('dim_customers') }} as customers
        on visits.customer_id = customers.customer_id
    where date_diff(
        'quarter', date_trunc('quarter', customers.signup_date), date_trunc('quarter', visits.visit_date)
    ) <= {{ horizon }}

)

select
    mart.customers as mart_customers,
    customers.customers as dim_customers,
    mart.visits as mart_visits,
    visits.visits as int_visits,
    mart.revenue as mart_revenue,
    visits.revenue as int_revenue,
from mart
cross join customers
cross join visits
where mart.customers != customers.customers
    or mart.visits != visits.visits
    or mart.revenue != visits.revenue
