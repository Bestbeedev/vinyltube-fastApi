import time
import os
from typing import Dict
from fastapi import Request
import re
from config import settings

# Rate limiting simple en mémoire
rate_limit_store: Dict[str, Dict] = {}

def validate_url(url: str) -> None:
    """Valide une URL YouTube"""
    if not url:
        raise ValueError("URL requise")
    
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtu\.be/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+'
    ]
    
    if not any(re.match(pattern, url) for pattern in youtube_patterns):
        raise ValueError("URL YouTube invalide")

def rate_limiter(request: Request, limit: int = None, window: int = None) -> bool:
    """Rate limiting simple par IP"""
    if limit is None:
        limit = settings.RATE_LIMIT_REQUESTS
    if window is None:
        window = settings.RATE_LIMIT_WINDOW
    
    client_ip = request.client.host
    current_time = time.time()
    
    # Nettoyer les anciennes entrées
    if client_ip in rate_limit_store:
        rate_limit_store[client_ip] = {
            req_time for req_time in rate_limit_store[client_ip]
            if current_time - req_time < window
        }
    else:
        rate_limit_store[client_ip] = set()
    
    # Vérifier la limite
    if len(rate_limit_store[client_ip]) >= limit:
        return False
    
    # Ajouter la requête actuelle
    rate_limit_store[client_ip].add(current_time)
    return True

def sanitize_filename(filename: str) -> str:
    """Nettoie un nom de fichier pour éviter les problèmes de système"""
    # Caractères non autorisés dans les noms de fichiers
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Limiter la longueur
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def validate_file_size(file_size: int, max_size: int = None) -> bool:
    """Valide la taille d'un fichier"""
    if max_size is None:
        max_size = settings.MAX_FILE_SIZE
    
    return 0 < file_size <= max_size
