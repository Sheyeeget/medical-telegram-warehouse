import os
import json
import glob
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# DB Config (matches your .env / docker-compose)
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "postgres"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_LAKE = BASE_DIR / "data" / "raw" / "telegram_messages"

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.telegram_messages (
                message_id BIGINT PRIMARY KEY,
                channel_name TEXT NOT NULL,
                message_date TIMESTAMP NOT NULL,
                message_text TEXT,
                has_media BOOLEAN,
                image_path TEXT,
                views INTEGER DEFAULT 0,
                forwards INTEGER DEFAULT 0,
                scraped_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        print("✅ Table 'raw.telegram_messages' ready.")

def load_data(conn):
    json_files = glob.glob(str(DATA_LAKE / "*" / "*.json"))
    all_records = []
    for f in json_files:
        with open(f, "r", encoding="utf-8") as file:
            all_records.extend(json.load(file))
    
    print(f"📊 Found {len(all_records)} total messages.")
    if not all_records:
        return

    insert_sql = """
        INSERT INTO raw.telegram_messages 
        (message_id, channel_name, message_date, message_text, has_media, image_path, views, forwards)
        VALUES %s
        ON CONFLICT (message_id) DO UPDATE SET
            views = EXCLUDED.views,
            forwards = EXCLUDED.forwards,
            image_path = EXCLUDED.image_path;
    """
    values = []
    for r in all_records:
        values.append((
            r["message_id"],
            r["channel_name"],
            datetime.fromisoformat(r["message_date"]),
            r["message_text"],
            r["has_media"],
            r["image_path"],
            r["views"],
            r["forwards"]
        ))
    
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, values, page_size=1000)
        conn.commit()
    print(f"✅ Loaded {len(values)} messages into PostgreSQL.")

if __name__ == "__main__":
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        create_table(conn)
        load_data(conn)
        conn.close()
        print("🎉 Data loading complete! Ready for dbt.")
    except Exception as e:
        print(f"❌ Error: {e}")