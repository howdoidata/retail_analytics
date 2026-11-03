-- One row per customer: signup date and location, first-touch acquisition channel, and the date of each
-- visit milestone in the `milestones` variable (one map column, so changing the milestones changes no schema).

{%- set milestones = var('milestones') | unique | sort | list %}

with

customers as (

    select * from {{ ref('stg_customers') }}

),

touches as (

    select * from {{ ref('stg_marketing_touches') }}

),

visits as (

    select * from {{ ref('int_customer_visits') }}

),

first_touches as (

    select
        customers.id as customer_id,
        touches.channel,
    from customers
    inner join touches
        on touches.customer_email = customers.email
        and touches.touched_at <= customers.created_at
    qualify row_number() over (
        partition by customers.id
        order by
            touches.touched_at,
            touches.id
    ) = 1

),

milestone_dates as (

    select
        customers.id as customer_id,
        cast(
            map(
                [{% for milestone in milestones %}{{ milestone }}{{ ', ' if not loop.last }}{% endfor %}],
                [
                    {%- for milestone in milestones %}
                    max(case when visits.visit_number = {{ milestone }} then visits.visit_date end)
                    {{- ',' if not loop.last }}
                    {%- endfor %}
                ]
            ) as map(integer, date)
        ) as milestone_dates,
    from customers
    left join visits
        on customers.id = visits.customer_id
    group by customers.id

),

final as (

    select
        customers.id as customer_id,
        cast(customers.created_at as date) as signup_date,
        customers.signup_location,
        first_touches.channel as acquisition_channel,
        milestone_dates.milestone_dates,
    from customers
    left join first_touches
        on customers.id = first_touches.customer_id
    left join milestone_dates
        on customers.id = milestone_dates.customer_id

)

select * from final
