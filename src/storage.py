"""Stockage des données (calendriers et événements)."""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from threading import Lock

from config import DATA_DIR
from logger import logger


class Storage:
    """Gestionnaire de stockage JSON simple."""
    
    def __init__(self, filename: str = "calendars.json"):
        self.filepath = os.path.join(DATA_DIR, filename)
        self.lock = Lock()
        self._data = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """Charge les données depuis le fichier."""
        if not os.path.exists(self.filepath):
            return {"calendars": {}, "events": {}}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Erreur chargement données: {e}")
            return {"calendars": {}, "events": {}}
    
    def _save(self) -> bool:
        """Sauvegarde les données dans le fichier."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, default=str)
            return True
        except IOError as e:
            logger.error(f"Erreur sauvegarde données: {e}")
            return False
    
    # === Calendriers ===
    
    def add_calendar(
        self,
        name: str,
        url: str,
        source: Optional[str] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Ajoute un nouveau calendrier."""
        with self.lock:
            calendar_id = str(uuid.uuid4())
            
            calendar = {
                "id": calendar_id,
                "name": name,
                "url": url,
                "source": source or self._detect_source(url),
                "enabled": enabled,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_sync": None,
                "event_count": 0
            }
            
            self._data["calendars"][calendar_id] = calendar
            self._save()
            
            logger.info(f"Calendrier ajouté: {name} ({calendar_id})")
            return calendar
    
    def _detect_source(self, url: str) -> str:
        """Détecte la source du calendrier à partir de l'URL."""
        url_lower = url.lower()
        if "airbnb" in url_lower:
            return "airbnb"
        elif "booking" in url_lower:
            return "booking"
        elif "vrbo" in url_lower or "homeaway" in url_lower:
            return "vrbo"
        elif "abritel" in url_lower:
            return "abritel"
        else:
            return "other"
    
    def get_calendar(self, calendar_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un calendrier par son ID."""
        return self._data["calendars"].get(calendar_id)
    
    def get_all_calendars(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Récupère tous les calendriers."""
        calendars = list(self._data["calendars"].values())
        if enabled_only:
            calendars = [c for c in calendars if c.get("enabled", True)]
        return calendars
    
    def get_calendar_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Récupère un calendrier par son URL (pour éviter les doublons)."""
        for calendar in self._data["calendars"].values():
            if calendar.get("url") == url:
                return calendar
        return None
    
    def update_calendar(self, calendar_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Met à jour un calendrier."""
        with self.lock:
            if calendar_id not in self._data["calendars"]:
                return None
            
            allowed_fields = {"name", "url", "source", "enabled", "last_sync", "event_count"}
            for key, value in kwargs.items():
                if key in allowed_fields:
                    self._data["calendars"][calendar_id][key] = value
            
            self._save()
            return self._data["calendars"][calendar_id]
    
    def delete_calendar(self, calendar_id: str) -> bool:
        """Supprime un calendrier et ses événements."""
        with self.lock:
            if calendar_id not in self._data["calendars"]:
                return False
            
            name = self._data["calendars"][calendar_id].get("name", "inconnu")
            
            # Supprimer les événements associés
            self._data["events"] = {
                uid: event for uid, event in self._data["events"].items()
                if event.get("calendar_id") != calendar_id
            }
            
            # Supprimer le calendrier
            del self._data["calendars"][calendar_id]
            self._save()
            
            logger.info(f"Calendrier supprimé: {name} ({calendar_id})")
            return True
    
    # === Événements ===
    
    def save_events(self, calendar_id: str, events: List[Dict[str, Any]]) -> int:
        """Sauvegarde les événements d'un calendrier."""
        with self.lock:
            # Supprimer les anciens événements du calendrier
            self._data["events"] = {
                uid: event for uid, event in self._data["events"].items()
                if event.get("calendar_id") != calendar_id
            }
            
            # Ajouter les nouveaux événements
            for event in events:
                uid = event.get("uid")
                if uid:
                    event["calendar_id"] = calendar_id
                    self._data["events"][uid] = event
            
            # Mettre à jour le compteur du calendrier
            if calendar_id in self._data["calendars"]:
                self._data["calendars"][calendar_id]["event_count"] = len(events)
                self._data["calendars"][calendar_id]["last_sync"] = \
                    datetime.now(timezone.utc).isoformat()
            
            self._save()
            return len(events)
    
    def get_events(self, calendar_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère les événements (tous ou par calendrier)."""
        events = list(self._data["events"].values())
        
        if calendar_id:
            events = [e for e in events if e.get("calendar_id") == calendar_id]
        
        # Trier par date de début
        events.sort(key=lambda x: x.get("start", ""))
        
        return events
    
    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
        calendar_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Récupère les événements dans une plage de dates."""
        events = self.get_events(calendar_id)
        
        filtered = []
        for event in events:
            event_start = event.get("start")
            event_end = event.get("end")
            
            # Convertir en datetime si nécessaire
            if isinstance(event_start, str):
                try:
                    event_start = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
                except ValueError:
                    continue
            
            if isinstance(event_end, str):
                try:
                    event_end = datetime.fromisoformat(event_end.replace("Z", "+00:00"))
                except ValueError:
                    event_end = event_start
            
            # Vérifier le chevauchement
            if event_start and event_end:
                if event_start <= end and event_end >= start:
                    filtered.append(event)
        
        return filtered
    
    # === Initialisation ===
    
    def init_default_calendars(self) -> int:
        """
        Charge les calendriers depuis les variables d'environnement 
        si aucun calendrier n'existe.
        
        Returns:
            Nombre de calendriers ajoutés
        """
        # Si des calendriers existent déjà, ne rien faire
        if self.get_all_calendars():
            logger.debug("Des calendriers existent déjà, pas d'initialisation")
            return 0
        
        added = 0
        
        # Configuration des calendriers par défaut
        default_calendars = [
            ("AIRBNB_ICS", "Airbnb"),
            ("BOOKING_ICS", "Booking.com"),
            # Ajouter d'autres sources ici si besoin
            ("VRBO_ICS", "VRBO"),
            ("ABRITEL_ICS", "Abritel"),
        ]
        
        for env_var, name in default_calendars:
            url = os.getenv(env_var)
            if url and url.strip():
                # Vérifier que ce n'est pas un exemple/placeholder
                if "example" in url.lower() or "12345" in url:
                    logger.warning(f"URL d'exemple ignorée pour {env_var}")
                    continue
                
                # Vérifier les doublons
                if self.get_calendar_by_url(url):
                    logger.warning(f"URL déjà existante, ignorée: {name}")
                    continue
                
                self.add_calendar(name=name, url=url)
                logger.info(f"✅ Calendrier '{name}' chargé depuis ${env_var}")
                added += 1
        
        if added > 0:
            logger.info(f"📅 {added} calendrier(s) par défaut initialisé(s)")
        else:
            logger.info("ℹ️  Aucun calendrier par défaut trouvé dans .env")
        
        return added


# Instance globale
storage = Storage()
