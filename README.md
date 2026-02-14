# 🚀 VinylTube Backend Python

Backend FastAPI pour VinylTube - Application de téléchargement de vidéos YouTube avec architecture moderne et robuste.

## 🏗️ Architecture

### Stack Technique
- **Framework**: FastAPI (Python 3.9+)
- **Téléchargement vidéo**: yt-dlp
- **Traitement vidéo**: ffmpeg-python
- **Validation**: Pydantic v2
- **Configuration**: pydantic-settings
- **Serveur**: Uvicorn

### Structure des Dossiers
```
backend/
├── main.py                 # Application FastAPI principale
├── config.py              # Configuration de l'application
├── models.py              # Pydantic models pour les API
├── requirements.txt       # Dépendances Python
├── .env                   # Configuration environnement
├── services/
│   ├── youtube_service.py  # Logique de téléchargement YouTube
│   └── file_service.py    # Gestion des fichiers
├── utils/
│   ├── validators.py      # Validation des URLs et rate limiting
│   └── cleanup.py         # Nettoyage automatique
├── downloads/             # Stockage temporaire des fichiers
└── static/               # Build du frontend Next.js
```

## 🚀 Installation et Démarrage

### Prérequis
- Python 3.9+
- FFmpeg (doit être installé sur le système)
- Node.js (pour le frontend)

### 1. Installation
```bash
# Cloner le projet et aller dans backend/
cd backend

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer .env selon vos besoins
nano .env
```

### 3. Build du Frontend (si nécessaire)
```bash
# Depuis la racine du projet Next.js
cd ../frontend
npm run build

# Copier le build dans le backend
cp -r out/* ../backend/static/
```

### 4. Démarrage
```bash
# Démarrer le backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Ou avec Python
python main.py
```

## 📡 API Endpoints

### endpoints principaux

#### Extraction des informations vidéo
```bash
POST /api/extract
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

#### Téléchargement vidéo
```bash
POST /api/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "itag": "137",
  "format": "video"
}
```

#### Service des fichiers
```bash
GET /api/download/file/{filename}
```

### endpoints de gestion

#### Health Check
```bash
GET /api/health
```

#### Statistiques
```bash
GET /api/stats
```

#### Liste des fichiers
```bash
GET /api/files
```

#### Suppression fichier
```bash
DELETE /api/files/{filename}
```

#### Nettoyage manuel
```bash
POST /api/cleanup
```

### endpoints frontend

#### Frontend Next.js
```bash
GET /                    # Page principale
GET /static/*            # Fichiers statiques
```

## 🔧 Configuration

### Variables d'environnement (.env)
```env
# Application
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Frontend
FRONTEND_URL=http://localhost:3000
FRONTEND_BUILD_PATH=./static

# Downloads
DOWNLOAD_DIR=./downloads
MAX_FILE_SIZE=524288000        # 500MB
CLEANUP_INTERVAL=3600          # 1 heure
FILE_RETENTION=86400           # 24 heures

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60           # secondes
```

## 🛠️ Fonctionnalités

### ✅ Fonctionnalités Implémentées
- **Extraction vidéo**: Informations complètes des vidéos YouTube
- **Téléchargement**: Support vidéo et audio avec conversion MP3
- **Rate limiting**: Protection contre les abus
- **Nettoyage automatique**: Suppression des fichiers anciens
- **Gestion fichiers**: Liste, suppression, statistiques
- **CORS**: Support pour frontend Next.js
- **Health checks**: Monitoring de l'état du service
- **Static files**: Sert le frontend Next.js
- **Validation**: Validation stricte des URLs YouTube
- **Error handling**: Gestion d'erreurs robuste

### 🔒 Sécurité
- Rate limiting par IP
- Validation des URLs YouTube
- Taille maximale des fichiers
- Trusted hosts middleware
- CORS configuré

### 🧹 Gestion des Fichiers
- Nettoyage automatique toutes les heures
- Suppression des fichiers de plus de 24h
- Statistiques d'utilisation
- Gestion de l'espace disque

## 🧪 Tests

### Test API avec curl
```bash
# Health check
curl http://localhost:8000/api/health

# Extract video info
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Download video
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "itag": "137", "format": "video"}'
```

### Test avec FastAPI docs
Visitez `http://localhost:8000/docs` pour l'interface interactive Swagger.

## 🐛 Dépannage

### Problèmes courants

#### FFmpeg non trouvé
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# Télécharger depuis https://ffmpeg.org/download.html
# Ajouter au PATH
```

#### Erreur de dépendances
```bash
# Réinstaller les dépendances
pip install -r requirements.txt --upgrade
```

#### Problèmes de permissions
```bash
# Vérifier les permissions du dossier downloads
chmod 755 downloads/
```

#### Port déjà utilisé
```bash
# Tuer le processus sur le port 8000
lsof -ti:8000 | xargs kill -9

# Ou utiliser un autre port
uvicorn main:app --port 8001
```

## 📊 Monitoring

### Logs
Le backend utilise les logs standards de Uvicorn. Pour plus de détails :
```bash
uvicorn main:app --log-level debug
```

### Métriques disponibles
- Nombre de fichiers téléchargés
- Espace disque utilisé
- Uptime du service
- Espace libre disponible

## � Docker Déploiement

### Build et Run (Développement)
```bash
# Build l'image Docker
make build

# Ou manuellement
docker build -t vinyltube-backend .

# Démarrer avec docker-compose
make run

# Ou manuellement
docker-compose up -d
```

### Production avec Nginx
```bash
# Mode production (avec nginx)
make prod

# Ou manuellement
docker-compose --profile production up -d
```

### Commandes Docker utiles
```bash
# Voir les logs
make logs

# Entrer dans le container
make shell

# Vérifier le health check
make health

# Arrêter tout
make stop

# Nettoyer
make clean
```

### Configuration Docker

#### Dockerfile
- **Base image** : Python 3.9-slim
- **FFmpeg** : Installé via apt
- **Sécurité** : Non-root user (appuser:1000)
- **Health check** : `/api/health` toutes les 30s

#### Docker Compose
- **Backend** : Port 8000
- **Nginx** : Ports 80/443 (production)
- **Volumes** : Downloads et static persistants
- **Restart** : unless-stopped

#### Environment Production
Copier `.env.production` et adapter :
```bash
cp .env.production .env
# Éditer .env avec votre domaine et settings
```

## �🚀 Déploiement

### Cloud Platforms

#### Railway
```bash
# Installer Railway CLI
npm install -g @railway/cli

# Déployer
railway login
railway up
```

#### Render
```bash
# Connecter repo GitHub
# Render va automatiquement détecter le Dockerfile
```

#### DigitalOcean App Platform
```bash
# Push sur GitHub
# Connecter repo dans DigitalOcean
# Activer App Platform
```

### Docker (optionnel)
```dockerfile
FROM python:3.9-slim

# Installer FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copier le backend
COPY backend/ /app/
WORKDIR /app

# Installer dépendances
RUN pip install -r requirements.txt

# Exposer le port
EXPOSE 8000

# Démarrer
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production
Pour la production, utilisez :
- **Gunicorn** + **Uvicorn workers**
- **Nginx** comme reverse proxy
- **Redis** pour le rate limiting distribué
- **S3/MinIO** pour le stockage des fichiers

## 📝 License

Ce projet est sous license MIT.
# vinyltube-fastApi
