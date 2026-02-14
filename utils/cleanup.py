import asyncio
import os
import time
from typing import List
from config import settings
from services.file_service import FileService

class CleanupScheduler:
    def __init__(self):
        self.running = False
        self.file_service = FileService()
    
    async def start(self):
        """Démarre le scheduler de nettoyage"""
        self.running = True
        print("🧹 Scheduler de nettoyage démarré")
        
        while self.running:
            try:
                await self.cleanup_old_files()
                await asyncio.sleep(settings.CLEANUP_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Erreur cleanup: {e}")
                await asyncio.sleep(60)  # Attendre 1 min en cas d'erreur
    
    async def cleanup_old_files(self):
        """Nettoie les fichiers plus vieux que FILE_RETENTION"""
        try:
            deleted_count = self.file_service.cleanup_old_files(settings.FILE_RETENTION)
            
            if deleted_count > 0:
                print(f"🧹 Nettoyé {deleted_count} fichiers anciens")
                
                # Afficher les statistiques après nettoyage
                stats = self.file_service.get_directory_stats()
                print(f"📊 Espace utilisé: {stats['total_size_mb']} MB ({stats['files_count']} fichiers)")
                
        except Exception as e:
            print(f"Erreur lors du nettoyage: {e}")
    
    async def force_cleanup(self):
        """Force un nettoyage immédiat"""
        await self.cleanup_old_files()
    
    def stop(self):
        """Arrête le scheduler"""
        self.running = False
        print("🛑 Scheduler de nettoyage arrêté")

class CleanupManager:
    """Gestionnaire de nettoyage avec fonctionnalités avancées"""
    
    def __init__(self):
        self.file_service = FileService()
    
    async def cleanup_by_size(self, max_total_size_mb: int = 1000) -> int:
        """Nettoie les fichiers les plus anciens pour respecter une taille maximale"""
        stats = self.file_service.get_directory_stats()
        
        if stats['total_size_mb'] <= max_total_size_mb:
            return 0
        
        # Trier les fichiers par date de modification (plus ancien d'abord)
        files = self.file_service.list_download_files()
        files.sort(key=lambda x: x['modified'])
        
        deleted_count = 0
        target_size = max_total_size_mb * 1024 * 1024  # Convertir en bytes
        current_size = stats['total_size_bytes']
        
        for file_info in files:
            if current_size <= target_size:
                break
            
            if self.file_service.delete_file(file_info['filename']):
                current_size -= file_info['size']
                deleted_count += 1
                print(f"🗑️ Supprimé: {file_info['filename']} ({file_info['size_mb']} MB)")
        
        if deleted_count > 0:
            print(f"🧹 Nettoyé {deleted_count} fichiers pour respecter la limite de {max_total_size_mb} MB")
        
        return deleted_count
    
    async def cleanup_orphaned_files(self) -> int:
        """Nettoie les fichiers orphelins (corrompus ou vides)"""
        files = self.file_service.list_download_files()
        deleted_count = 0
        
        for file_info in files:
            file_path = file_info['filepath']
            
            # Vérifier si le fichier est vide
            if file_info['size'] == 0:
                if self.file_service.delete_file(file_info['filename']):
                    deleted_count += 1
                    print(f"🗑️ Supprimé fichier vide: {file_info['filename']}")
                continue
            
            # Vérifier si le fichier est lisible (pas corrompu)
            try:
                with open(file_path, 'rb') as f:
                    f.read(1024)  # Lire les premiers 1KB pour vérifier
            except (IOError, OSError):
                if self.file_service.delete_file(file_info['filename']):
                    deleted_count += 1
                    print(f"🗑️ Supprimé fichier corrompu: {file_info['filename']}")
        
        if deleted_count > 0:
            print(f"🧹 Nettoyé {deleted_count} fichiers orphelins")
        
        return deleted_count
    
    def get_cleanup_report(self) -> dict:
        """Génère un rapport de nettoyage"""
        stats = self.file_service.get_directory_stats()
        files = self.file_service.list_download_files()
        
        # Calculer l'âge des fichiers
        current_time = time.time()
        file_ages = []
        
        for file_info in files:
            age_hours = (current_time - file_info['modified']) / 3600
            file_ages.append({
                'filename': file_info['filename'],
                'age_hours': round(age_hours, 1),
                'size_mb': file_info['size_mb']
            })
        
        # Trier par âge (plus ancien d'abord)
        file_ages.sort(key=lambda x: x['age_hours'], reverse=True)
        
        return {
            'total_files': len(files),
            'total_size_mb': stats['total_size_mb'],
            'free_space_mb': stats['free_space_mb'],
            'oldest_files': file_ages[:5],  # 5 fichiers les plus anciens
            'files_older_than_24h': len([f for f in file_ages if f['age_hours'] > 24]),
            'files_older_than_1week': len([f for f in file_ages if f['age_hours'] > 168]),
            'cleanup_threshold_mb': settings.FILE_RETENTION / 3600  # heures
        }
