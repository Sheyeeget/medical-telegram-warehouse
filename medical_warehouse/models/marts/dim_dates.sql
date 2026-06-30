WITH date_spine AS (
    SELECT DISTINCT CAST(message_date AS DATE) AS full_date
    FROM {{ ref('stg_telegram_messages') }}
)
SELECT
    CAST(TO_CHAR(full_date, 'YYYYMMDD') AS INTEGER) AS date_key,
    full_date,
    EXTRACT(DOY FROM full_date) AS day_of_year,
    EXTRACT(ISOYEAR FROM full_date) AS iso_year,
    EXTRACT(WEEK FROM full_date) AS week_of_year,
    EXTRACT(MONTH FROM full_date) AS month,
    TO_CHAR(full_date, 'Month') AS month_name,
    EXTRACT(QUARTER FROM full_date) AS quarter,
    EXTRACT(YEAR FROM full_date) AS year,
    CASE WHEN EXTRACT(ISODOW FROM full_date) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM date_spine