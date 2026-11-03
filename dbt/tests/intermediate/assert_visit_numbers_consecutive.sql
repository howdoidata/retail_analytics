-- Every customer's visit numbers run 1, 2, 3, ... with no gaps (uniqueness is the grain test).

select
    customer_id,
    min(visit_number) as first_visit_number,
    max(visit_number) as last_visit_number,
    count(*) as visits,
from {{ ref('int_customer_visits') }}
group by customer_id
having min(visit_number) != 1
    or max(visit_number) != count(*)
