from pydantic import BaseModel, HttpUrl, validator
from typing import List, Optional
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

class DownloadJobResponse(BaseModel):
    job_id: str
    message: str = "Téléchargement démarré"

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    dependencies: dict
    uptime: float
