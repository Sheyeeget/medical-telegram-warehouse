cat > medical_warehouse/models/marts/fct_image_detections.sql << 'EOF'
SELECT
    id.detection_id,
    id.message_id,
    dc.channel_key,
    dd.date_key,
    id.image_category,
    id.num_objects,
    id.top_detection,
    id.top_confidence,
    id.processed_at
FROM analytics.image_detections id
LEFT JOIN dim_channels dc ON id.channel_name = dc.channel_name
LEFT JOIN dim_dates dd ON CAST(id.processed_at AS DATE) = dd.full_date
EOF