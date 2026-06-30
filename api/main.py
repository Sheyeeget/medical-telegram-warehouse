from fastapi import FastAPI, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from .database import SessionLocal
from .schemas import (
    ProductResponse,
    ChannelActivityResponse,
    MessageSearchResponse,
    VisualContentResponse
)

app = FastAPI(
    title="Medical Telegram Analytics API",
    description="API for analyzing Ethiopian medical Telegram data",
    version="1.0.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Medical Telegram Analytics API", "status": "running"}

@app.get("/api/reports/top-products", response_model=List[ProductResponse])
def get_top_products(limit: int = Query(10, ge=1, le=50)):
    db = next(get_db())
    query = text("""
        SELECT 
            word,
            mention_count,
            channels
        FROM (
            SELECT 
                LOWER(TRIM(word)) AS word,
                COUNT(*) AS mention_count,
                ARRAY_AGG(DISTINCT channel_name) AS channels
            FROM (
                SELECT 
                    channel_name,
                    UNNEST(STRING_TO_ARRAY(message_text, ' ')) AS word
                FROM raw.telegram_messages
                WHERE message_text IS NOT NULL 
                  AND LENGTH(message_text) > 10
            ) t
            WHERE LENGTH(word) > 3
              AND word NOT IN ('the','and','for','are','but','not','you','all','can','had','her','was','one','our','out','has','its','his','from','this','have','with','your','that','they','what','when','where','who','which','will','would','could','should','ethiopia','ethiopian','pharmaceutical','medical','health','care','drug','pharmacy','medication','treatment','disease','hospital','clinic','doctor','nurse','patient','medicine','drugs','pharma','healthcare')
            GROUP BY word
            ORDER BY mention_count DESC
            LIMIT :limit
        ) subquery
    """)
    result = db.execute(query, {"limit": limit})
    products = []
    for row in result:
        products.append(ProductResponse(
            product_name=row[0],
            mention_count=row[1],
            channels=row[2] if row[2] else []
        ))
    db.close()
    return products

@app.get("/api/channels/{channel_name}/activity", response_model=List[ChannelActivityResponse])
def get_channel_activity(channel_name: str):
    db = next(get_db())
    query = text("""
        SELECT 
            dc.channel_name,
            dd.full_date::text AS date,
            COUNT(fm.message_id) AS message_count,
            COALESCE(AVG(fm.views), 0) AS avg_views
        FROM neondb_marts.fct_messages fm
        LEFT JOIN neondb_marts.dim_channels dc ON fm.channel_key = dc.channel_key
        LEFT JOIN neondb_marts.dim_dates dd ON fm.date_key = dd.date_key
        WHERE dc.channel_name = :channel_name
        GROUP BY dc.channel_name, dd.full_date
        ORDER BY dd.full_date DESC
        LIMIT 30
    """)
    result = db.execute(query, {"channel_name": channel_name})
    activities = []
    for row in result:
        activities.append(ChannelActivityResponse(
            channel_name=row[0],
            date=row[1],
            message_count=row[2],
            avg_views=row[3]
        ))
    db.close()
    return activities

@app.get("/api/search/messages", response_model=List[MessageSearchResponse])
def search_messages(query: str = Query(..., min_length=3),
                    limit: int = Query(20, ge=1, le=100)):
    db = next(get_db())
    sql = text("""
        SELECT 
            fm.message_id,
            dc.channel_name,
            dd.full_date AS message_date,
            fm.message_text,
            fm.views
        FROM neondb_marts.fct_messages fm
        LEFT JOIN neondb_marts.dim_channels dc ON fm.channel_key = dc.channel_key
        LEFT JOIN neondb_marts.dim_dates dd ON fm.date_key = dd.date_key
        WHERE LOWER(fm.message_text) LIKE LOWER(:query)
        ORDER BY fm.views DESC
        LIMIT :limit
    """)
    result = db.execute(sql, {"query": f'%{query}%', "limit": limit})
    messages = []
    for row in result:
        messages.append(MessageSearchResponse(
            message_id=row[0],
            channel_name=row[1],
            message_date=row[2],
            message_text=row[3][:200] if row[3] else '',
            views=row[4] if row[4] else 0
        ))
    db.close()
    return messages

@app.get("/api/reports/visual-content", response_model=List[VisualContentResponse])
def get_visual_content_stats():
    db = next(get_db())
    query = text("""
        SELECT 
            channel_name,
            COUNT(*) AS total_images,
            SUM(CASE WHEN image_category = 'promotional' THEN 1 ELSE 0 END) AS promotional,
            SUM(CASE WHEN image_category = 'product_display' THEN 1 ELSE 0 END) AS product_display,
            SUM(CASE WHEN image_category = 'lifestyle' THEN 1 ELSE 0 END) AS lifestyle,
            SUM(CASE WHEN image_category = 'other' THEN 1 ELSE 0 END) AS other
        FROM analytics.image_detections
        GROUP BY channel_name
    """)
    result = db.execute(query)
    stats = []
    for row in result:
        stats.append(VisualContentResponse(
            channel_name=row[0],
            total_images=row[1],
            promotional=row[2] or 0,
            product_display=row[3] or 0,
            lifestyle=row[4] or 0,
            other=row[5] or 0
        ))
    db.close()
    return stats
