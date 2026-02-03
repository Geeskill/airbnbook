"""Configuration de l'application AirbnBook."""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'application
APP_NAME = "AirbnBook"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Configuration API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_KEY = os.getenv("API_KEY", None)  # None = pas d'auth requise

# Configuration de synchronisation
SYNC_INTERVAL = max(1, int(os.getenv("SYNC_INTERVAL", 30)))  # Minimum 1 minute
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))  # Timeout en secondes
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# Configuration des chemins
DATA_DIR = os.getenv("DATA_DIR", "data")
LOGS_DIR = os.getenv("LOGS_DIR", "logs")

# Créer les dossiers s'ils n'existent pas
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Configuration du logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.path.join(LOGS_DIR, "airbnbook.log")
