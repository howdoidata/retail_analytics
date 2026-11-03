-- M6: no test account survives staging (an `@example.com` email, or a first or last name `test`).

select
    id,
    email,
    first_name,
    last_name,
from {{ ref('stg_customers') }}
where email like '%@example.com'
    or lower(trim(first_name)) = 'test'
    or lower(trim(last_name)) = 'test'
