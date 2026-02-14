from pydantic import BaseModel, HttpUrl, validator
from typing import List, Optional, Literal
from enum import Enum

class FormatType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"

class VideoFormat(BaseModel):
    itag: str
    quality: str
    container: str
    hasAudio: bool
    hasVideo: bool
    fileSize: Optional[str] = None
    type: FormatType

class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    author: str
    duration: int
    formats: List[VideoFormat]
    videoId: str
    url: HttpUrl

class ExtractRequest(BaseModel):
    url: HttpUrl
    
    @validator('url')
    def validate_youtube_url(cls, v):
        if not any(x in str(v) for x in ['youtube.com', 'youtu.be']):
            raise ValueError('URL YouTube invalide')
        return v

class DownloadRequest(BaseModel):
    url: HttpUrl
    itag: str
    format: FormatType

class DownloadResponse(BaseModel):
    success: bool
    downloadUrl: str
    filename: str
    fileSize: str
    duration: Optional[int] = None
    message: str = "Fichier prêt pour le téléchargement"

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    dependencies: dict
    uptime: float
