-- Fails if any message date is in the future
SELECT *
FROM {{ ref('fct_messages') }} f
LEFT JOIN {{ ref('dim_dates') }} d ON f.date_key = d.date_key
WHERE d.full_date > CURRENT_DATE