-- Within each channel and cohort month, the cohort's customers_reached never rises from one milestone to the
-- next in milestone order.

with

stepped as (

    select
        channel,
        cohort_month,
        milestone,
        customers_reached,
        lag(customers_reached) over (
            partition by channel, cohort_month
            order by milestone
        ) as previous_reached,
    from {{ ref('fct_visit_funnel_by_channel') }}

)

select * from stepped
where customers_reached > previous_reached
