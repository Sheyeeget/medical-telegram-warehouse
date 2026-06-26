import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaPhoto
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged
import socks

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER", "")  # Optional for 2FA

# Channels to scrape (exactly as per the spec)
CHANNELS = [
    "CheMed123",
    "lobelia4cosmetics",
    "tikvahpharma",
    # Add more from et.tgstat.com/medicine here if you find them
]

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_LAKE = BASE_DIR / "data" / "raw" / "telegram_messages"
IMAGES_DIR = BASE_DIR / "data" / "raw" / "images"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
DATA_LAKE.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def scrape_channel(client, channel_username, limit=500):
    """
    Scrape messages from a single channel.
    Saves JSON files partitioned by date and downloads images.
    """
    logger.info(f"Starting scrape for channel: {channel_username}")
    
    try:
        entity = await client.get_entity(f"https://t.me/{channel_username}")
    except Exception as e:
        logger.error(f"Could not find channel {channel_username}: {e}")
        return

    # Dictionary to hold messages grouped by date (YYYY-MM-DD)
    messages_by_date = {}

    try:
        # Iterate over messages (most recent first)
        async for message in client.iter_messages(entity, limit=limit):
            # Extract basic fields
            msg_date = message.date
            date_str = msg_date.strftime("%Y-%m-%d")
            
            # Build the message record
            record = {
                "message_id": message.id,
                "channel_name": channel_username,
                "message_date": msg_date.isoformat(),
                "message_text": message.text or "",
                "has_media": bool(message.media),
                "image_path": None,
                "views": message.views if message.views is not None else 0,
                "forwards": message.forwards if message.forwards is not None else 0,
            }

            # --- Handle Image Download (if media is a photo) ---
            if message.media and isinstance(message.media, MessageMediaPhoto):
                try:
                    # Create channel-specific image folder
                    channel_img_dir = IMAGES_DIR / channel_username
                    channel_img_dir.mkdir(parents=True, exist_ok=True)
                    
                    # File path: data/raw/images/{channel}/{message_id}.jpg
                    img_path = channel_img_dir / f"{message.id}.jpg"
                    
                    # Download the photo
                    await client.download_media(message, file=str(img_path))
                    record["image_path"] = str(img_path.relative_to(BASE_DIR))
                    logger.debug(f"Downloaded image: {img_path}")
                except Exception as e:
                    logger.warning(f"Failed to download image for msg {message.id}: {e}")

            # Append to the date-based list
            if date_str not in messages_by_date:
                messages_by_date[date_str] = []
            messages_by_date[date_str].append(record)

            # Log progress every 100 messages
            if len(messages_by_date[date_str]) % 100 == 0:
                logger.info(f"Scraped {len(messages_by_date[date_str])} messages for {date_str}")

    except FloodWaitError as e:
        logger.warning(f"Rate limited on {channel_username}. Waiting {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Unexpected error scraping {channel_username}: {e}")

    # --- Write JSON files to the Data Lake ---
    for date_str, records in messages_by_date.items():
        # Partition structure: data/raw/telegram_messages/YYYY-MM-DD/channel_name.json
        date_dir = DATA_LAKE / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = date_dir / f"{channel_username}.json"
        
        # If file exists, load and extend (to handle incremental scraping later)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            # Merge: simple approach - combine and dedupe by message_id
            all_records = {r["message_id"]: r for r in existing + records}
            records_to_write = list(all_records.values())
        else:
            records_to_write = records

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records_to_write, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(records_to_write)} messages to {file_path}")

    logger.info(f"Finished scraping {channel_username}. Total date partitions: {len(messages_by_date)}")


async def main():
    # Validate credentials
    if API_ID == 0 or not API_HASH:
        logger.error("Missing TELEGRAM_API_ID or TELEGRAM_API_HASH in .env file.")
        return

    # Initialize the Telegram client
    client = TelegramClient("session_name", API_ID, API_HASH)
    
    try:
        await client.start(phone=PHONE_NUMBER if PHONE_NUMBER else None)
        logger.info("Connected to Telegram API successfully.")
        
        # Scrape all channels sequentially (to avoid global rate limits)
        for channel in CHANNELS:
            await scrape_channel(client, channel, limit=300)  # Adjust limit as needed
            
    except Exception as e:
        logger.error(f"Failed to connect or scrape: {e}")
    finally:
        await client.disconnect()
        logger.info("Disconnected from Telegram.")


if __name__ == "__main__":
    asyncio.run(main())