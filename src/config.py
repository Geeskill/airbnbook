"""Configuration centralisée de l'application AirbnBook."""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


class Config:
    """Configuration de l'application."""
    
    # === Application ===
    APP_NAME = "AirbnBook"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    
    # === API ===
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_KEY = os.getenv("API_KEY")  # None si non défini = pas d'auth
    
    # === Synchronisation ===
    SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "30"))  # minutes
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # secondes
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    # === Sources par défaut (optionnel via .env) ===
    AIRBNB_ICS_URL = os.getenv("AIRBNB_ICS_URL")
    BOOKING_ICS_URL = os.getenv("BOOKING_ICS_URL")
    PROPERTY_NAME = os.getenv("PROPERTY_NAME", "Mon logement")
    
    # === Stockage ===
    DATA_DIR = os.getenv("DATA_DIR", "data")
    SOURCES_FILE = os.path.join(DATA_DIR, "sources.json")
    EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
    
    # === Logs ===
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # === Export ICS ===
    OUTFILE = os.path.join(DATA_DIR, "calendar.ics")
    OUTFILE_FR = os.path.join(DATA_DIR, "calendar-fr.ics")
    
    @classmethod
    def ensure_directories(cls):
        """Crée les répertoires nécessaires s'ils n'existent pas."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)
    
    @classmethod
    def display(cls):
        """Affiche la configuration actuelle (pour debug)."""
        print(f"APP_NAME: {cls.APP_NAME}")
        print(f"APP_VERSION: {cls.APP_VERSION}")
        print(f"DEBUG: {cls.DEBUG}")
        print(f"API_HOST: {cls.API_HOST}")
        print(f"API_PORT: {cls.API_PORT}")
        print(f"API_KEY: {'***' if cls.API_KEY else 'Non défini'}")
        print(f"SYNC_INTERVAL: {cls.SYNC_INTERVAL} min")
        print(f"DATA_DIR: {cls.DATA_DIR}")
        print(f"LOG_DIR: {cls.LOG_DIR}")


# Créer les répertoires au chargement du module
Config.ensure_directories()
