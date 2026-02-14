import os
import shutil
from typing import List, Dict
from config import settings

class FileService:
    def __init__(self):
        self.download_dir = settings.DOWNLOAD_DIR
    
    def ensure_directories(self):
        """Crée les dossiers nécessaires s'ils n'existent pas"""
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(settings.FRONTEND_BUILD_PATH, exist_ok=True)
    
    def get_file_info(self, filename: str) -> Dict:
        """Retourne les informations d'un fichier"""
        file_path = os.path.join(self.download_dir, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier {filename} non trouvé")
        
        stat = os.stat(file_path)
        
        return {
            'filename': filename,
            'filepath': file_path,
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created': stat.st_ctime,
            'modified': stat.st_mtime,
            'download_url': f"/api/download/file/{filename}"
        }
    
    def list_download_files(self) -> List[Dict]:
        """Liste tous les fichiers dans le dossier downloads"""
        if not os.path.exists(self.download_dir):
            return []
        
        files = []
        for filename in os.listdir(self.download_dir):
            file_path = os.path.join(self.download_dir, filename)
            if os.path.isfile(file_path):
                try:
                    files.append(self.get_file_info(filename))
                except Exception:
                    continue
        
        # Trier par date de modification (plus récent d'abord)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files
    
    def delete_file(self, filename: str) -> bool:
        """Supprime un fichier spécifique"""
        file_path = os.path.join(self.download_dir, filename)
        
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def cleanup_old_files(self, max_age_seconds: int = None) -> int:
        """Nettoie les fichiers plus vieux que max_age_seconds"""
        if max_age_seconds is None:
            max_age_seconds = settings.FILE_RETENTION
        
        if not os.path.exists(self.download_dir):
            return 0
        
        current_time = os.path.getmtime(self.download_dir)
        deleted_count = 0
        
        for filename in os.listdir(self.download_dir):
            file_path = os.path.join(self.download_dir, filename)
            
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception:
                        continue
        
        return deleted_count
    
    def get_directory_stats(self) -> Dict:
        """Retourne les statistiques du dossier downloads"""
        if not os.path.exists(self.download_dir):
            return {
                'files_count': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'free_space_bytes': 0,
                'free_space_mb': 0
            }
        
        files = self.list_download_files()
        total_size = sum(f['size'] for f in files)
        
        # Espace libre sur le disque
        total, used, free = shutil.disk_usage(self.download_dir)
        
        return {
            'files_count': len(files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'free_space_bytes': free,
            'free_space_mb': round(free / (1024 * 1024), 2),
            'directory_path': self.download_dir
        }
    
    def validate_file_size(self, filename: str) -> bool:
        """Valide que le fichier ne dépasse pas la taille maximale"""
        try:
            file_info = self.get_file_info(filename)
            return file_info['size'] <= settings.MAX_FILE_SIZE
        except FileNotFoundError:
            return False
