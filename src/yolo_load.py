import os
import json
import csv
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

print("🔄 Loading YOLO results to PostgreSQL...")

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
    "database": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

# Read CSV
csv_path = Path("data/processed/yolo_results/yolo_detections.csv")
if not csv_path.exists():
    print("❌ CSV file not found! Run yolo_detect.py first.")
    exit()

print(f"📂 Reading: {csv_path}")

results = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        results.append({
            'message_id': int(row['message_id']),
            'channel': row['channel'],
            'image_category': row['image_category'],
            'num_objects': int(row['num_objects']),
            'top_detection': row['top_detection'] if row['top_detection'] != '' else None,
            'top_confidence': float(row['top_confidence']) if row['top_confidence'] != '' else 0,
            'processed_at': row['processed_at']
        })

print(f"📊 Found {len(results)} results to load.")

try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Connected to PostgreSQL!")
    
    # Insert without ON CONFLICT (we already have UNIQUE constraint)
    insert_sql = """
        INSERT INTO analytics.image_detections 
        (message_id, channel_name, image_category, num_objects, 
         top_detection, top_confidence, processed_at)
        VALUES %s
    """
    
    values = []
    for r in results:
        values.append((
            r['message_id'],
            r['channel'],
            r['image_category'],
            r['num_objects'],
            r['top_detection'],
            r['top_confidence'],
            r['processed_at']
        ))
    
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, values, page_size=100)
        conn.commit()
    
    conn.close()
    print(f"✅ Loaded {len(results)} YOLO results into PostgreSQL.")
    print("🎉 YOLO enrichment complete!")
    
except Exception as e:
    print(f"❌ Database error: {e}")