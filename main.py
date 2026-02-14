from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import os
import asyncio
from contextlib import asynccontextmanager

from config import settings
from models import (
    ExtractRequest, DownloadRequest, VideoInfo, 
    DownloadResponse, HealthResponse
)
from services.youtube_service import YouTubeService
from services.file_service import FileService
from utils.cleanup import CleanupScheduler
from utils.validators import validate_url, rate_limiter

# Variables globales
youtube_service = YouTubeService()
file_service = FileService()
cleanup_scheduler = CleanupScheduler()
start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle de l'application"""
    # Démarrage
    print(f"🚀 {settings.APP_NAME} v{settings.VERSION} démarré")
    print(f"📁 Dossier downloads: {settings.DOWNLOAD_DIR}")
    
    # Créer les dossiers nécessaires
    file_service.ensure_directories()
    
    # Démarrer le scheduler de nettoyage
    cleanup_task = asyncio.create_task(cleanup_scheduler.start())
    
    yield
    
    # Arrêt
    cleanup_task.cancel()
    print("👋 Backend arrêté")

# Créer l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Backend Python pour VinylTube - Téléchargement YouTube",
    lifespan=lifespan
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
)

# Servir les fichiers statiques du frontend
if os.path.exists(os.path.join(settings.FRONTEND_BUILD_PATH, "index.html")):
    app.mount("/static", StaticFiles(directory=settings.FRONTEND_BUILD_PATH), name="static")

@app.get("/")
async def serve_frontend():
    """Servir le frontend Next.js"""
    frontend_path = os.path.join(settings.FRONTEND_BUILD_PATH, "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return JSONResponse({"message": "Frontend non trouvé. Build le frontend Next.js d'abord."})

@app.post("/api/extract-fast")
async def extract_video_info_fast(request: Request, body: ExtractRequest):
    """Extrait les informations de base d'une vidéo YouTube (rapide)"""
    try:
        # Rate limiting
        if not rate_limiter(request):
            raise HTTPException(status_code=429, detail="Trop de requêtes")
        
        # Validation
        validate_url(str(body.url))
        
        # Extraction rapide (sans formats)
        video_id = youtube_service.extract_video_id(str(body.url))
        if not video_id:
            raise ValueError("URL YouTube invalide")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True, # Plus rapide
            'socket_timeout': 5,
            'retries': 1,
        }
        
        loop = asyncio.get_event_loop()
        
        def _extract_info():
            import yt_dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(str(body.url), download=False)
        
        info = await asyncio.wait_for(
            loop.run_in_executor(None, _extract_info), 
            timeout=10.0  # 10 secondes timeout
        )
        
        # Retourner seulement les infos de base
        return {
            "title": info.get('title', 'Video sans titre'),
            "thumbnail": info.get('thumbnail', f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'),
            "author": info.get('uploader', 'YouTube'),
            "duration": info.get('duration', 0),
            "videoId": video_id,
            "url": str(body.url),
            "formats": [], # Vide pour le mode rapide
            "fastMode": True
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"❌ Erreur extraction rapide: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.post("/api/extract")
async def extract_video_info(request: Request, body: ExtractRequest):
    """Extrait les informations d'une vidéo YouTube"""
    try:
        # Rate limiting
        if not rate_limiter(request):
            raise HTTPException(status_code=429, detail="Trop de requêtes")
        
        # Validation
        validate_url(str(body.url))
        
        # Extraction
        video_info = await youtube_service.extract_video_info(str(body.url))
        
        return video_info
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"❌ Erreur extraction: {str(e)}")
        print(f"❌ Type erreur: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.post("/api/download")
async def download_video(request: Request, body: DownloadRequest):
    """Prépare et sert le téléchargement d'une vidéo"""
    try:
        # Rate limiting
        if not rate_limiter(request):
            raise HTTPException(status_code=429, detail="Trop de requêtes")
        
        # Validation
        validate_url(str(body.url))
        
        # Téléchargement
        download_info = await youtube_service.download_video(
            str(body.url), 
            body.itag, 
            body.format
        )
        
        return DownloadResponse(
            success=True,
            downloadUrl=download_info['downloadUrl'],
            filename=download_info['filename'],
            fileSize=download_info['fileSize'],
            message="Fichier prêt pour le téléchargement"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors du téléchargement")

@app.get("/api/download/file/{filename:path}")
async def serve_file(filename: str):
    """Sert un fichier téléchargé"""
    try:
        # Décoder le nom de fichier
        import urllib.parse
        decoded_filename = urllib.parse.unquote(filename)
        
        file_path = os.path.join(settings.DOWNLOAD_DIR, decoded_filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Fichier non trouvé")
        
        # Vérifier la taille du fichier
        file_size = os.path.getsize(file_path)
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux")
        
        return FileResponse(
            file_path,
            filename=decoded_filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors du service du fichier")

@app.get("/api/health")
async def health_check():
    """Vérifie l'état du backend"""
    try:
        # Vérifier les dépendances
        import yt_dlp
        import ffmpeg
        
        dependencies = {
            'yt-dlp': getattr(yt_dlp, '__version__', yt_dlp.version.__version__ if hasattr(yt_dlp, 'version') else 'unknown'),
            'ffmpeg-python': getattr(ffmpeg, '__version__', 'unknown'),
        }
        
        # Vérifier l'espace disque
        import shutil
        total, used, free = shutil.disk_usage(settings.DOWNLOAD_DIR)
        
        return HealthResponse(
            status="healthy",
            version=settings.VERSION,
            dependencies=dependencies,
            uptime=time.time() - start_time
        )
        
    except Exception as e:
        return JSONResponse(
            {
                "status": "unhealthy",
                "error": str(e),
                "version": settings.VERSION
            },
            status_code=503
        )

@app.get("/api/stats")
async def get_stats():
    """Statistiques du backend"""
    try:
        stats = file_service.get_directory_stats()
        
        return {
            "downloads_count": stats['files_count'],
            "total_size_mb": stats['total_size_mb'],
            "uptime_seconds": time.time() - start_time,
            "download_dir": settings.DOWNLOAD_DIR,
            "free_space_mb": stats['free_space_mb']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
async def list_files():
    """Liste tous les fichiers téléchargés"""
    try:
        files = file_service.list_download_files()
        return {
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """Supprime un fichier spécifique"""
    try:
        success = file_service.delete_file(filename)
        if success:
            return {"message": f"Fichier {filename} supprimé avec succès"}
        else:
            raise HTTPException(status_code=404, detail="Fichier non trouvé")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cleanup")
async def trigger_cleanup():
    """Déclenche un nettoyage manuel"""
    try:
        await cleanup_scheduler.force_cleanup()
        return {"message": "Nettoyage déclenché avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
