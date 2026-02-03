"""Stockage des données (sources et événements)."""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from threading import Lock

from src.config import Config
from src.logger import get_logger

logger = get_logger(__name__)


class Storage:
    """Gestionnaire de stockage JSON."""
    
    def __init__(self):
        self._lock = Lock()
        self._sources_file = Config.SOURCES_FILE
        self._events_file = Config.EVENTS_FILE
        
        # Créer les répertoires si nécessaire
        Config.ensure_directories()
        
        # Initialiser les fichiers s'ils n'existent pas
        self._init_files()
    
    def _init_files(self):
        """Initialise les fichiers JSON s'ils n'existent pas."""
        if not os.path.exists(self._sources_file):
            self._write_json(self._sources_file, [])
            logger.debug(f"Fichier créé: {self._sources_file}")
        
        if not os.path.exists(self._events_file):
            self._write_json(self._events_file, [])
            logger.debug(f"Fichier créé: {self._events_file}")
    
    def _read_json(self, filepath: str) -> Any:
        """Lit un fichier JSON."""
        try:
            with self._lock:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans {filepath}: {e}")
            return []
    
    def _write_json(self, filepath: str, data: Any):
        """Écrit dans un fichier JSON."""
        with self._lock:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    # =========================================================================
    # SOURCES (calendriers)
    # =========================================================================
    
    def get_sources(self) -> List[Dict]:
        """Récupère toutes les sources."""
        return self._read_json(self._sources_file)
    
    def get_source(self, source_id: str) -> Optional[Dict]:
        """Récupère une source par ID."""
        sources = self.get_sources()
        for source in sources:
            if source.get("id") == source_id:
                return source
        return None
    
    def add_source(self, name: str, url: str, source_type: str = "other", enabled: bool = True) -> Dict:
        """Ajoute une nouvelle source."""
        sources = self.get_sources()
        
        # Vérifier si l'URL existe déjà
        for source in sources:
            if source.get("url") == url:
                logger.warning(f"Source avec URL déjà existante: {url}")
                return source
        
        new_source = {
            "id": str(uuid.uuid4()),
            "name": name,
            "url": url,
            "type": source_type,  # airbnb, booking, other
            "enabled": enabled,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_sync": None,
            "last_error": None,
            "event_count": 0
        }
        
        sources.append(new_source)
        self._write_json(self._sources_file, sources)
        logger.info(f"Source ajoutée: {name} ({source_type})")
        
        return new_source
    
    def update_source(self, source_id: str, updates: Dict) -> Optional[Dict]:
        """Met à jour une source."""
        sources = self.get_sources()
        
        for i, source in enumerate(sources):
            if source.get("id") == source_id:
                # Champs non modifiables
                updates.pop("id", None)
                updates.pop("created_at", None)
                
                # Mettre à jour
                source.update(updates)
                source["updated_at"] = datetime.now(timezone.utc).isoformat()
                sources[i] = source
                
                self._write_json(self._sources_file, sources)
                logger.info(f"Source mise à jour: {source_id}")
                return source
        
        return None
    
    def delete_source(self, source_id: str) -> bool:
        """Supprime une source et ses événements."""
        sources = self.get_sources()
        initial_count = len(sources)
        
        sources = [s for s in sources if s.get("id") != source_id]
        
        if len(sources) < initial_count:
            self._write_json(self._sources_file, sources)
            
            # Supprimer les événements associés
            self.delete_events_by_source(source_id)
            
            logger.info(f"Source supprimée: {source_id}")
            return True
        
        return False
    
    def init_default_sources(self) -> int:
        """Initialise les sources par défaut depuis la config."""
        added = 0
        
        if Config.AIRBNB_ICS_URL:
            self.add_source(
                name=f"{Config.PROPERTY_NAME} - Airbnb",
                url=Config.AIRBNB_ICS_URL,
                source_type="airbnb"
            )
            added += 1
        
        if Config.BOOKING_ICS_URL:
            self.add_source(
                name=f"{Config.PROPERTY_NAME} - Booking",
                url=Config.BOOKING_ICS_URL,
                source_type="booking"
            )
            added += 1
        
        if added > 0:
            logger.info(f"{added} source(s) par défaut initialisée(s)")
        
        return added
    
    # =========================================================================
    # ÉVÉNEMENTS
    # =========================================================================
    
    def get_events(self, source_id: Optional[str] = None) -> List[Dict]:
        """Récupère les événements, optionnellement filtrés par source."""
        events = self._read_json(self._events_file)
        
        if source_id:
            events = [e for e in events if e.get("source_id") == source_id]
        
        return events
    
    def get_all_events(self) -> List[Dict]:
        """Récupère tous les événements."""
        return self._read_json(self._events_file)
    
    def save_events(self, source_id: str, new_events: List[Dict]) -> int:
        """Sauvegarde les événements d'une source (remplace les existants)."""
        all_events = self.get_events()
        
        # Retirer les anciens événements de cette source
        all_events = [e for e in all_events if e.get("source_id") != source_id]
        
        # Ajouter les nouveaux événements
        for event in new_events:
            event["source_id"] = source_id
            event["synced_at"] = datetime.now(timezone.utc).isoformat()
            all_events.append(event)
        
        self._write_json(self._events_file, all_events)
        
        # Mettre à jour le compteur de la source
        self.update_source(source_id, {"event_count": len(new_events)})
        
        logger.debug(f"Sauvegardé {len(new_events)} événements pour source {source_id}")
        return len(new_events)
    
    def delete_events_by_source(self, source_id: str) -> int:
        """Supprime tous les événements d'une source."""
        events = self.get_events()
        initial_count = len(events)
        
        events = [e for e in events if e.get("source_id") != source_id]
        deleted = initial_count - len(events)
        
        if deleted > 0:
            self._write_json(self._events_file, events)
            logger.debug(f"Supprimé {deleted} événements de la source {source_id}")
        
        return deleted
    
    def clear_all(self):
        """Supprime toutes les données (pour tests)."""
        self._write_json(self._sources_file, [])
        self._write_json(self._events_file, [])
        logger.warning("Toutes les données ont été supprimées")


# Instance globale (optionnel, pour compatibilité)
storage = Storage()
