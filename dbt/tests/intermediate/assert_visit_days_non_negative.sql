-- No visit before signup or before the previous visit, and days since the previous visit is null on visit 1
-- and only there.

select
    customer_id,
    visit_number,
    days_since_signup,
    days_since_previous_visit,
from {{ ref('int_customer_visits') }}
where days_since_signup < 0
    or days_since_previous_visit < 0
    or (visit_number = 1) != (days_since_previous_visit is null)
