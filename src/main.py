"""Point d'entrée principal de l'application AirbnBook."""

import signal
import sys
import time
import threading
from typing import Optional

import uvicorn

from config import (
    APP_NAME,
    APP_VERSION,
    API_HOST,
    API_PORT,
    SYNC_INTERVAL,
    DEBUG
)
from logger import logger
from storage import storage
from sync_service import sync_all_calendars


class AirbnBook:
    """Application principale AirbnBook."""
    
    def __init__(self):
        self.running = False
        self.sync_thread: Optional[threading.Thread] = None
        
        # Configurer les handlers de signaux
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Gère les signaux d'arrêt."""
        logger.info(f"Signal {signum} reçu, arrêt en cours...")
        self.stop()
    
    def _sync_loop(self):
        """Boucle de synchronisation périodique."""
        logger.info(f"Démarrage de la boucle de sync (intervalle: {SYNC_INTERVAL} min)")
        
        while self.running:
            try:
                calendars = storage.get_all_calendars()
                
                if calendars:
                    logger.info(f"Synchronisation automatique de {len(calendars)} calendrier(s)")
                    results = sync_all_calendars(calendars)
                    
                    # Sauvegarder les événements
                    for result in results:
                        if result["success"] and "events" in result:
                            storage.save_events(result["calendar_id"], result["events"])
                else:
                    logger.debug("Aucun calendrier à synchroniser")
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de sync: {e}")
            
            # Attendre avec vérification périodique pour permettre l'arrêt
            for _ in range(SYNC_INTERVAL * 60):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("Boucle de synchronisation arrêtée")
    
    def start(self):
        """Démarre l'application."""
        logger.info(f"{'='*50}")
        logger.info(f"  {APP_NAME} v{APP_VERSION}")
        logger.info(f"{'='*50}")
        logger.info(f"Mode debug: {DEBUG}")
        logger.info(f"API: http://{API_HOST}:{API_PORT}")
        logger.info(f"Intervalle de sync: {SYNC_INTERVAL} minutes")
        
        self.running = True
        
        # Démarrer la boucle de sync dans un thread séparé
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        
        # Démarrer le serveur API (bloquant)
        try:
            uvicorn.run(
                "api:app",
                host=API_HOST,
                port=API_PORT,
                reload=DEBUG,
                log_level="info" if DEBUG else "warning"
            )
        except Exception as e:
            logger.error(f"Erreur serveur API: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête l'application proprement."""
        if not self.running:
            return
        
        logger.info("Arrêt de l'application...")
        self.running = False
        
        # Attendre la fin du thread de sync
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        
        logger.info("Application arrêtée")


def main():
    """Point d'entrée."""
    app = AirbnBook()
    app.start()


if __name__ == "__main__":
    main()
