"""Point d'entrée principal de l'application AirbnBook."""

import signal
import sys
import time
import threading
import asyncio
from typing import Optional

import uvicorn

from src.config import Config
from src.logger import get_logger
from src.storage import Storage
from src.sync_service import SyncService

# Logger
logger = get_logger("main")


class AirbnBook:
    """Application principale AirbnBook."""
    
    def __init__(self):
        self.running = False
        self.sync_thread: Optional[threading.Thread] = None
        self.storage = Storage()
        self.sync_service = SyncService(self.storage)
        
        # Configurer les handlers de signaux
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Gère les signaux d'arrêt."""
        logger.info(f"Signal {signum} reçu, arrêt en cours...")
        self.stop()
    
    def _sync_loop(self):
        """Boucle de synchronisation périodique."""
        logger.info(f"Démarrage de la boucle de sync (intervalle: {Config.SYNC_INTERVAL} min)")
        
        # Première synchronisation immédiate
        self._do_sync()
        
        while self.running:
            # Attendre avec vérification périodique pour permettre l'arrêt
            for _ in range(Config.SYNC_INTERVAL * 60):
                if not self.running:
                    break
                time.sleep(1)
            
            if self.running:
                self._do_sync()
        
        logger.info("Boucle de synchronisation arrêtée")
    
    def _do_sync(self):
        """Effectue une synchronisation."""
        try:
            sources = self.storage.get_sources()
            enabled_sources = [s for s in sources if s.get("enabled", True)]
            
            if enabled_sources:
                logger.info(f"🔄 Synchronisation de {len(enabled_sources)} source(s)...")
                
                # Exécuter la sync async dans un event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.sync_service.sync_all())
                finally:
                    loop.close()
                
                logger.info(
                    f"✅ Sync terminée: {result.get('sources_synced', 0)}/{len(enabled_sources)} source(s), "
                    f"{result.get('events_count', 0)} événement(s)"
                )
            else:
                logger.debug("Aucune source active à synchroniser")
                
        except Exception as e:
            logger.error(f"Erreur dans la synchronisation: {e}", exc_info=Config.DEBUG)
    
    def _init_sources(self):
        """Initialise les sources par défaut depuis .env si nécessaire."""
        logger.info("Vérification des sources de calendriers...")
        
        existing = self.storage.get_sources()
        
        if existing:
            logger.info(f"📅 {len(existing)} source(s) existante(s):")
            for source in existing:
                status = "✓" if source.get("enabled", True) else "○"
                logger.info(f"   {status} {source['name']} ({source.get('source_type', 'inconnu')})")
        else:
            # Charger les sources par défaut depuis .env
            added = self._load_default_sources()
            if added == 0:
                logger.warning(
                    "⚠️  Aucune source configurée. "
                    "Ajoutez-en via l'API ou configurez AIRBNB_ICS_URL/BOOKING_ICS_URL dans .env"
                )
    
    def _load_default_sources(self) -> int:
        """Charge les sources par défaut depuis les variables d'environnement."""
        added = 0
        
        # Charger Airbnb si configuré
        if Config.AIRBNB_ICS_URL:
            source = {
                "id": "default_airbnb",
                "name": "Airbnb (défaut)",
                "url": Config.AIRBNB_ICS_URL,
                "source_type": "airbnb",
                "property_name": Config.PROPERTY_NAME,
                "enabled": True,
                "created_at": None
            }
            self.storage.add_source(source)
            logger.info(f"✅ Source Airbnb ajoutée depuis .env")
            added += 1
        
        # Charger Booking si configuré
        if Config.BOOKING_ICS_URL:
            source = {
                "id": "default_booking",
                "name": "Booking (défaut)",
                "url": Config.BOOKING_ICS_URL,
                "source_type": "booking",
                "property_name": Config.PROPERTY_NAME,
                "enabled": True,
                "created_at": None
            }
            self.storage.add_source(source)
            logger.info(f"✅ Source Booking ajoutée depuis .env")
            added += 1
        
        return added
    
    def start(self):
        """Démarre l'application."""
        logger.info(f"{'='*50}")
        logger.info(f"  🏠 {Config.APP_NAME} v{Config.APP_VERSION}")
        logger.info(f"{'='*50}")
        logger.info(f"Mode debug: {Config.DEBUG}")
        logger.info(f"API: http://{Config.API_HOST}:{Config.API_PORT}")
        logger.info(f"Intervalle de sync: {Config.SYNC_INTERVAL} minutes")
        logger.info(f"Documentation: http://{Config.API_HOST}:{Config.API_PORT}/api/docs")
        logger.info("")
        
        # Initialiser les sources par défaut
        self._init_sources()
        
        self.running = True
        
        # Démarrer la boucle de sync dans un thread séparé
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("🔄 Thread de synchronisation démarré")
        
        # Démarrer le serveur API (bloquant)
        logger.info(f"🚀 Démarrage du serveur API...")
        try:
            uvicorn.run(
                "src.api:app",
                host=Config.API_HOST,
                port=Config.API_PORT,
                reload=Config.DEBUG,
                log_level="debug" if Config.DEBUG else "warning",
                access_log=Config.DEBUG
            )
        except Exception as e:
            logger.error(f"Erreur serveur API: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête l'application proprement."""
        if not self.running:
            return
        
        logger.info("🛑 Arrêt de l'application...")
        self.running = False
        
        # Attendre la fin du thread de sync
        if self.sync_thread and self.sync_thread.is_alive():
            logger.debug("Attente de la fin du thread de sync...")
            self.sync_thread.join(timeout=5)
            if self.sync_thread.is_alive():
                logger.warning("Le thread de sync n'a pas pu être arrêté proprement")
        
        logger.info("👋 Application arrêtée")
        sys.exit(0)


def main():
    """Point d'entrée."""
    app = AirbnBook()
    app.start()


if __name__ == "__main__":
    main()
