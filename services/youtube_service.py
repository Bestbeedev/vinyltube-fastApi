import yt_dlp
import asyncio
import uuid
import os
import urllib.parse
import re
import json
from typing import List, Dict, Optional, AsyncGenerator
from models import VideoInfo, VideoFormat, FormatType
from config import settings

import shutil
from yt_dlp.networking.impersonate import ImpersonateTarget

_download_jobs: Dict[str, Dict] = {}

# Chemin ffmpeg résolu une seule fois au démarrage
_FFMPEG_LOCATION = shutil.which('ffmpeg') or '/usr/local/bin/ffmpeg'


_YOUTUBE_DOMAINS = re.compile(r'youtube\.com|youtu\.be')


class YouTubeService:
    def __init__(self):
        self._base_opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ffmpeg_location': _FFMPEG_LOCATION,
            'extractor_args': {
                'youtube': {
                    'player_client': ['mweb'],
                },
                'youtubepot-bgutilhttp': {
                    'base_url': os.environ.get('YTPOT_SERVER_URL', 'http://127.0.0.1:4416'),
                },
            }
        }
        self._youtube_extra: dict = {}
        self._impersonate_opts = {
            'impersonate': ImpersonateTarget('chrome'),
        }

    def _is_youtube(self, url: str) -> bool:
        return bool(_YOUTUBE_DOMAINS.search(url))

    def _platform_opts(self, url: str) -> dict:
        """Retourne les options spécifiques à la plateforme."""
        if self._is_youtube(url):
            return self._youtube_extra
        return self._impersonate_opts

    def extract_video_id(self, url: str) -> str:
        yt = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&?\n]+)', url)
        if yt:
            return yt.group(1)
        segment = re.search(r'/([^/?#]+)(?:[?#]|$)', url)
        return segment.group(1) if segment else 'video'

    async def extract_video_info(self, url: str) -> VideoInfo:
        if not url:
            raise ValueError("URL requise")

        video_id = self.extract_video_id(url)

        ydl_opts = {
            **self._base_opts,
            **self._platform_opts(url),
            'extract_flat': False,
            'socket_timeout': 15,
            'retries': 3,
            'extractor_retries': 5,
        }

        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.wait_for(
                loop.run_in_executor(None, _extract),
                timeout=20.0
            )

            formats = []
            for fmt in info.get('formats', []):
                if fmt.get('vcodec') != 'none' or fmt.get('acodec') != 'none':
                    formats.append(VideoFormat(
                        itag=str(fmt.get('format_id', '')),
                        quality=fmt.get('format_note') or fmt.get('resolution') or fmt.get('height') and f"{fmt['height']}p" or 'Unknown',
                        container=fmt.get('ext', 'mp4'),
                        hasAudio=fmt.get('acodec') != 'none',
                        hasVideo=fmt.get('vcodec') != 'none',
                        fileSize=self._format_file_size(fmt.get('filesize')),
                        type=FormatType.VIDEO if fmt.get('vcodec') != 'none' else FormatType.AUDIO
                    ))

            return VideoInfo(
                title=info.get('title', 'Vidéo sans titre'),
                thumbnail=info.get('thumbnail') or '',
                author=info.get('uploader') or info.get('channel') or 'Inconnu',
                duration=info.get('duration') or 0,
                formats=formats,
                videoId=video_id,
                url=url
            )

        except Exception as e:
            raise RuntimeError(f"Erreur extraction: {str(e)}")

    def _format_file_size(self, size_bytes: Optional[int]) -> Optional[str]:
        if size_bytes is None:
            return None
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    # ── SSE / Jobs ────────────────────────────────────────────────────────────

    async def start_download_job(self, url: str, itag: str, format_type: FormatType) -> str:
        job_id = str(uuid.uuid4())
        _download_jobs[job_id] = {"status": "pending", "progress": 0}

        async def _run():
            try:
                result = await self.download_video(url, itag, format_type, job_id=job_id)
                _download_jobs[job_id].update({"status": "done", "progress": 100, **result})
            except Exception as e:
                _download_jobs[job_id].update({"status": "error", "error": str(e)})

        asyncio.create_task(_run())
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict]:
        return _download_jobs.get(job_id)

    async def stream_job_progress(self, job_id: str) -> AsyncGenerator[str, None]:
        last_progress = -1
        while True:
            job = _download_jobs.get(job_id)
            if job is None:
                yield f"data: {json.dumps({'error': 'job introuvable'})}\n\n"
                break

            progress = job["progress"]
            status = job["status"]

            if progress != last_progress or status in ("done", "error"):
                last_progress = progress
                payload: Dict = {"progress": progress, "status": status}
                if status == "done":
                    payload["downloadUrl"] = job.get("downloadUrl")
                    payload["filename"] = job.get("filename")
                    payload["fileSize"] = job.get("fileSize")
                if status == "error":
                    payload["error"] = job.get("error")
                yield f"data: {json.dumps(payload)}\n\n"

            if status in ("done", "error"):
                _download_jobs.pop(job_id, None)
                break

            await asyncio.sleep(0.4)

    # ── Téléchargement ────────────────────────────────────────────────────────

    async def download_video(self, url: str, itag: str, format_type: FormatType, job_id: str = None) -> Dict:
        download_opts = {
            **self._base_opts,
            **self._platform_opts(url),
            'format': itag,
            'outtmpl': f'{settings.DOWNLOAD_DIR}/%(title)s_[%(id)s].%(ext)s',
            'postprocessors': [],
            'socket_timeout': 60,
            'retries': 5,
            'extractor_retries': 5,
            'fragment_retries': 10,
            'retry_sleep_functions': {
                'http': lambda n: min(30, (n + 1) * 2),
                'fragment': lambda n: min(30, (n + 1) * 2),
            },
        }

        if job_id and job_id in _download_jobs:
            def _progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded = d.get('downloaded_bytes', 0)
                    if total:
                        _download_jobs[job_id]['progress'] = min(round(downloaded / total * 100, 1), 99)
                elif d['status'] == 'finished':
                    _download_jobs[job_id]['progress'] = 99
            download_opts['progress_hooks'] = [_progress_hook]

        if format_type == FormatType.AUDIO:
            download_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
            download_opts['format'] = 'bestaudio/best'

        loop = asyncio.get_running_loop()

        # Capture le vrai filepath après post-processing (ex: .webm -> .mp3)
        final_filepath: Dict = {}

        def _postprocessor_hook(d):
            if d.get('status') == 'finished' and d.get('info_dict'):
                final_filepath['path'] = d['info_dict'].get('filepath') or d.get('filepath')

        download_opts['postprocessor_hooks'] = [_postprocessor_hook]

        def _download():
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        try:
            fallback_filepath = await asyncio.wait_for(
                loop.run_in_executor(None, _download),
                timeout=120.0
            )

            # Utiliser le filepath capturé par le hook, sinon fallback
            filepath = final_filepath.get('path') or fallback_filepath

            # Si le fichier n'existe pas (renommé par ffmpeg), chercher par stem
            if not os.path.exists(filepath):
                stem = os.path.splitext(os.path.basename(fallback_filepath))[0]
                for f in os.listdir(settings.DOWNLOAD_DIR):
                    if f.startswith(stem[:50]):
                        filepath = os.path.join(settings.DOWNLOAD_DIR, f)
                        break

            if not os.path.exists(filepath):
                raise RuntimeError(f"Fichier introuvable après téléchargement: {filepath}")

            file_size = os.path.getsize(filepath)
            if file_size == 0:
                raise RuntimeError("Le fichier téléchargé est vide")

            filename = os.path.basename(filepath)
            download_url = f"/api/download/file/{urllib.parse.quote(filename)}"

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
