WITH source AS (
    SELECT
        message_id,
        channel_name,
        message_date,
        message_text,
        has_media,
        image_path,
        views,
        forwards,
        scraped_at
    FROM raw.telegram_messages
    WHERE message_text IS NOT NULL 
      AND LENGTH(TRIM(message_text)) > 0
)
SELECT
    message_id,
    channel_name,
    message_date,
    message_text,
    LENGTH(message_text) AS message_length,
    has_media,
    image_path,
    views,
    forwards,
    scraped_at
FROM source
