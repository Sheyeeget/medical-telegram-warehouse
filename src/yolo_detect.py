import os
import sys
import json
import csv
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

# Force print to show immediately
sys.stdout.reconfigure(line_buffering=True)

load_dotenv()

print("🚀 Starting YOLO detection...", flush=True)

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "data" / "raw" / "images"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "yolo_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"📂 Image directory: {IMAGES_DIR}", flush=True)

# Check if images directory exists
if not IMAGES_DIR.exists():
    print(f"❌ Image directory not found: {IMAGES_DIR}", flush=True)
    sys.exit(1)

# Find all images
image_files = list(IMAGES_DIR.rglob("*.jpg")) + list(IMAGES_DIR.rglob("*.png"))
print(f"📸 Found {len(image_files)} images to process.", flush=True)

if not image_files:
    print("❌ No images found!", flush=True)
    sys.exit(1)

# Load YOLO model
print("🔄 Loading YOLO model (this may take a moment)...", flush=True)
model = YOLO("yolov8n.pt")
print("✅ YOLO model loaded!", flush=True)

# Classification rules
def classify_image(boxes, model):
    has_person = False
    has_product = False
    
    product_classes = ['bottle', 'cup', 'bowl', 'apple', 'orange', 'banana', 
                       'cake', 'pizza', 'sandwich', 'hot dog', 'donut', 
                       'book', 'vase', 'tv', 'laptop', 'mouse', 'keyboard',
                       'cell phone', 'microwave', 'oven', 'refrigerator']
    
    for box in boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = model.names[class_id]
        
        if confidence > 0.5:
            if class_name == 'person':
                has_person = True
            if class_name in product_classes:
                has_product = True
    
    if has_person and has_product:
        return 'promotional'
    elif has_product and not has_person:
        return 'product_display'
    elif has_person and not has_product:
        return 'lifestyle'
    else:
        return 'other'

results = []
total = len(image_files)

for idx, img_path in enumerate(image_files):
    try:
        # Extract message_id and channel from path
        channel = img_path.parent.name
        message_id = int(img_path.stem)
        
        # Run YOLO detection
        detections = model(img_path)
        boxes = detections[0].boxes
        
        # Extract detection details
        detected_objects = []
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            detected_objects.append({
                'class': class_name,
                'confidence': confidence,
                'bbox': [x1, y1, x2, y2]
            })
        
        # Classify image
        image_category = classify_image(boxes, model)
        
        # Store result
        result = {
            'message_id': message_id,
            'channel': channel,
            'image_path': str(img_path.relative_to(BASE_DIR)),
            'detected_objects': detected_objects,
            'num_objects': len(detected_objects),
            'image_category': image_category,
            'top_detection': detected_objects[0]['class'] if detected_objects else None,
            'top_confidence': detected_objects[0]['confidence'] if detected_objects else 0,
            'processed_at': datetime.now().isoformat()
        }
        results.append(result)
        
        # Print progress every 10 images
        if (idx + 1) % 10 == 0:
            print(f"✅ Processed {idx + 1}/{total} images", flush=True)
            
    except Exception as e:
        print(f"❌ Error processing {img_path}: {e}", flush=True)

print(f"💾 Saving results to CSV...", flush=True)

# Save results to CSV
csv_path = OUTPUT_DIR / "yolo_detections.csv"
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['message_id', 'channel', 'image_category', 'num_objects', 
                     'top_detection', 'top_confidence', 'processed_at'])
    for r in results:
        writer.writerow([
            r['message_id'],
            r['channel'],
            r['image_category'],
            r['num_objects'],
            r['top_detection'],
            r['top_confidence'],
            r['processed_at']
        ])

print(f"💾 Results saved to {csv_path}", flush=True)
print(f"📊 Total processed: {len(results)} images", flush=True)

# Load to PostgreSQL
print("🔄 Loading results to PostgreSQL...", flush=True)

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT"),
    "database": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Connected to PostgreSQL!", flush=True)
    
    # Create table if not exists
    with conn.cursor() as cur:
        cur.execute("""
            CREATE SCHEMA IF NOT EXISTS analytics;
            CREATE TABLE IF NOT EXISTS analytics.image_detections (
                detection_id SERIAL PRIMARY KEY,
                message_id BIGINT NOT NULL,
                channel_name TEXT NOT NULL,
                image_category TEXT NOT NULL,
                num_objects INTEGER DEFAULT 0,
                top_detection TEXT,
                top_confidence FLOAT,
                processed_at TIMESTAMP DEFAULT NOW(),
                detected_objects JSONB
            );
        """)
        conn.commit()
        print("✅ Table ready!", flush=True)
    
    # Insert results
    insert_sql = """
        INSERT INTO analytics.image_detections 
        (message_id, channel_name, image_category, num_objects, 
         top_detection, top_confidence, processed_at, detected_objects)
        VALUES %s
        ON CONFLICT (message_id) DO UPDATE SET
            image_category = EXCLUDED.image_category,
            num_objects = EXCLUDED.num_objects,
            top_detection = EXCLUDED.top_detection,
            top_confidence = EXCLUDED.top_confidence,
            detected_objects = EXCLUDED.detected_objects;
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
            r['processed_at'],
            json.dumps(r['detected_objects'])
        ))
    
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, values, page_size=100)
        conn.commit()
    
    conn.close()
    print(f"✅ Loaded {len(results)} YOLO results into PostgreSQL.", flush=True)
    print("🎉 YOLO enrichment complete!", flush=True)
    
except Exception as e:
    print(f"❌ Database error: {e}", flush=True)

print("🏁 Done!", flush=True)