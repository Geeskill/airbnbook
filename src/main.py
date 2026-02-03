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
        
        # Première synchronisation immédiate
        self._do_sync()
        
        while self.running:
            # Attendre avec vérification périodique pour permettre l'arrêt
            for _ in range(SYNC_INTERVAL * 60):
                if not self.running:
                    break
                time.sleep(1)
            
            if self.running:
                self._do_sync()
        
        logger.info("Boucle de synchronisation arrêtée")
    
    def _do_sync(self):
        """Effectue une synchronisation."""
        try:
            calendars = storage.get_all_calendars(enabled_only=True)
            
            if calendars:
                logger.info(f"🔄 Synchronisation de {len(calendars)} calendrier(s)...")
                results = sync_all_calendars(calendars)
                
                # Traiter les résultats
                success_count = 0
                total_events = 0
                
                for result in results:
                    if result.get("success") and "events" in result:
                        calendar_id = result["calendar_id"]
                        events = result["events"]
                        storage.save_events(calendar_id, events)
                        success_count += 1
                        total_events += len(events)
                    elif not result.get("success"):
                        logger.warning(
                            f"Échec sync {result.get('calendar_name', 'inconnu')}: "
                            f"{result.get('error', 'erreur inconnue')}"
                        )
                
                logger.info(
                    f"✅ Sync terminée: {success_count}/{len(calendars)} calendrier(s), "
                    f"{total_events} événement(s)"
                )
            else:
                logger.debug("Aucun calendrier actif à synchroniser")
                
        except Exception as e:
            logger.error(f"Erreur dans la synchronisation: {e}", exc_info=DEBUG)
    
    def _init_calendars(self):
        """Initialise les calendriers par défaut depuis .env si nécessaire."""
        logger.info("Vérification des calendriers...")
        
        existing = storage.get_all_calendars()
        if existing:
            logger.info(f"📅 {len(existing)} calendrier(s) existant(s):")
            for cal in existing:
                status = "✓" if cal.get("enabled", True) else "○"
                logger.info(f"   {status} {cal['name']} ({cal.get('source', 'inconnu')})")
        else:
            # Charger les calendriers par défaut depuis .env
            added = storage.init_default_calendars()
            if added == 0:
                logger.warning(
                    "⚠️  Aucun calendrier configuré. "
                    "Ajoutez-en via l'API ou configurez AIRBNB_ICS/BOOKING_ICS dans .env"
                )
    
    def start(self):
        """Démarre l'application."""
        logger.info(f"{'='*50}")
        logger.info(f"  🏠 {APP_NAME} v{APP_VERSION}")
        logger.info(f"{'='*50}")
        logger.info(f"Mode debug: {DEBUG}")
        logger.info(f"API: http://{API_HOST}:{API_PORT}")
        logger.info(f"Intervalle de sync: {SYNC_INTERVAL} minutes")
        logger.info("")
        
        # Initialiser les calendriers par défaut
        self._init_calendars()
        
        self.running = True
        
        # Démarrer la boucle de sync dans un thread séparé
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("🔄 Thread de synchronisation démarré")
        
        # Démarrer le serveur API (bloquant)
        logger.info(f"🚀 Démarrage du serveur API...")
        try:
            uvicorn.run(
                "api:app",
                host=API_HOST,
                port=API_PORT,
                reload=DEBUG,
                log_level="debug" if DEBUG else "warning",
                access_log=DEBUG
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
