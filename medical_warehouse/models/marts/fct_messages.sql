SELECT
    s.message_id,
    dc.channel_key,
    dd.date_key,
    s.message_text,
    s.message_length,
    s.views,
    s.forwards,
    s.has_media
FROM {{ ref('stg_telegram_messages') }} s
LEFT JOIN {{ ref('dim_channels') }} dc ON s.channel_name = dc.channel_name
LEFT JOIN {{ ref('dim_dates') }} dd ON CAST(s.message_date AS DATE) = dd.full_date