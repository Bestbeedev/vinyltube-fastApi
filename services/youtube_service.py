import yt_dlp
import asyncio
from typing import List, Dict, Optional
from models import VideoInfo, VideoFormat, FormatType
from config import settings
import re

class YouTubeService:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extrait l'ID vidéo d'une URL YouTube"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&?\n]+)',
            r'youtube\.com\/watch\?.*v=([^&?\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def extract_video_info(self, url: str) -> VideoInfo:
        """Extrait les informations complètes d'une vidéo"""
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError("URL YouTube invalide")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'listformats': True,
            'socket_timeout': 10,
            'retries': 3,
            # Options pour contourner les restrictions YouTube
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web', 'android', 'web_music'],
                    'player_skip': ['configs', 'webpage'],
                }
            },
            'extractor_retries': 5,
            'nocheckcertificate': True,
        }
        
        loop = asyncio.get_event_loop()
        
        def _extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        try:
            info = await asyncio.wait_for(
                loop.run_in_executor(None, _extract_info), 
                timeout=20.0  # 20 secondes timeout
            )
            
            # Formater les formats disponibles
            formats = []
            for fmt in info.get('formats', []):
                if fmt.get('vcodec') != 'none' or fmt.get('acodec') != 'none':
                    video_format = VideoFormat(
                        itag=str(fmt.get('format_id', '')),
                        quality=fmt.get('format_note', fmt.get('resolution', 'Unknown')),
                        container=fmt.get('ext', 'mp4'),
                        hasAudio=fmt.get('acodec') != 'none',
                        hasVideo=fmt.get('vcodec') != 'none',
                        fileSize=self._format_file_size(fmt.get('filesize')),
                        type=FormatType.VIDEO if fmt.get('vcodec') != 'none' else FormatType.AUDIO
                    )
                    formats.append(video_format)
            
            return VideoInfo(
                title=info.get('title', 'Video sans titre'),
                thumbnail=info.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'),
                author=info.get('uploader', 'YouTube'),
                duration=info.get('duration', 0),
                formats=formats,
                videoId=video_id,
                url=url
            )
            
        except Exception as e:
            raise RuntimeError(f"Erreur extraction vidéo: {str(e)}")
    
    def _format_file_size(self, size_bytes: Optional[int]) -> Optional[str]:
        """Formate la taille du fichier en MB"""
        if size_bytes is None:
            return None
        size_mb = size_bytes / (1024 * 1024)
        return f"{size_mb:.1f} MB"
    
    async def download_video(self, url: str, itag: str, format_type: FormatType) -> Dict:
        """Télécharge une vidéo et retourne les infos du fichier"""
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError("URL YouTube invalide")
        
        # Configuration de téléchargement améliorée pour contourner les restrictions
        download_opts = {
            'format': itag,
            'outtmpl': f'{settings.DOWNLOAD_DIR}/%(title)s_[%(id)s].%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [],
            'socket_timeout': 60,
            'retries': 5,
            # Options pour contourner les restrictions YouTube
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web', 'android', 'web_music'],
                    'player_skip': ['configs', 'webpage'],
                }
            },
            'extractor_retries': 5,
            'fragment_retries': 10,
            'retry_sleep_functions': {
                'http': lambda n: min(30, (n + 1) * 2),
                'fragment': lambda n: min(30, (n + 1) * 2),
            },
            'nocheckcertificate': True,
        }
        
        # Ajouter des post-processeurs selon le format
        if format_type == FormatType.AUDIO:
            download_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
            download_opts['format'] = 'bestaudio/best'
        
        loop = asyncio.get_event_loop()
        
        def _download():
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        try:
            filepath = await asyncio.wait_for(
                loop.run_in_executor(None, _download), 
                timeout=120.0  # 2 minutes timeout pour le téléchargement
            )
            
            # Obtenir les infos du fichier
            import os
            file_size = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            
            # Créer une URL de téléchargement relative avec encodage correct
            import urllib.parse
            encoded_filename = urllib.parse.quote(filename)
            download_url = f"/api/download/file/{encoded_filename}"
            
            return {
                'filepath': filepath,
                'filename': filename,
                'downloadUrl': download_url,
                'fileSize': self._format_file_size(file_size),
                'success': True
            }
            
        except asyncio.TimeoutError:
            raise RuntimeError("Timeout lors du téléchargement")
        except Exception as e:
            raise RuntimeError(f"Erreur téléchargement: {str(e)}")
