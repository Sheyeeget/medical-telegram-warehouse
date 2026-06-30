from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductResponse(BaseModel):
    product_name: str
    mention_count: int
    channels: List[str]

class ChannelActivityResponse(BaseModel):
    channel_name: str
    date: str
    message_count: int
    avg_views: float

class MessageSearchResponse(BaseModel):
    message_id: int
    channel_name: str
    message_date: datetime
    message_text: str
    views: int

class VisualContentResponse(BaseModel):
    channel_name: str
    total_images: int
    promotional: int
    product_display: int
    lifestyle: int
    other: int
