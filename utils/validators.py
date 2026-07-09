import time
import os
from typing import Dict
from fastapi import Request
import re
from config import settings

rate_limit_store: Dict[str, Dict] = {}

# Plateformes supportées par yt-dlp (non exhaustif, pour validation de base)
SUPPORTED_DOMAINS = [
    'youtube.com', 'youtu.be',
    'vimeo.com',
    'twitter.com', 'x.com',
    'instagram.com',
    'tiktok.com',
    'dailymotion.com',
    'twitch.tv',
    'reddit.com',
    'facebook.com', 'fb.watch',
    'soundcloud.com',
    'bilibili.com',
    'rumble.com',
    'odysee.com',
]

def validate_url(url: str) -> None:
    """Valide une URL supportée par yt-dlp"""
    if not url:
        raise ValueError("URL requise")

    if not re.match(r'https?://', url):
        raise ValueError("URL invalide — doit commencer par http:// ou https://")

def rate_limiter(request: Request, limit: int = None, window: int = None) -> bool:
    """Rate limiting simple par IP"""
    if limit is None:
        limit = settings.RATE_LIMIT_REQUESTS
    if window is None:
        window = settings.RATE_LIMIT_WINDOW

    client_ip = request.client.host
    current_time = time.time()

    if client_ip in rate_limit_store:
        rate_limit_store[client_ip] = {
            req_time for req_time in rate_limit_store[client_ip]
            if current_time - req_time < window
        }
    else:
        rate_limit_store[client_ip] = set()

    if len(rate_limit_store[client_ip]) >= limit:
        return False

    rate_limit_store[client_ip].add(current_time)
    return True

def sanitize_filename(filename: str) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename

def validate_file_size(file_size: int, max_size: int = None) -> bool:
    if max_size is None:
        max_size = settings.MAX_FILE_SIZE
    return 0 < file_size <= max_size
