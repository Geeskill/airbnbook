"""Service de synchronisation des calendriers iCal."""

import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import REQUEST_TIMEOUT, MAX_RETRIES
from logger import logger
from ical_parser import parse_ical


# Session HTTP avec retry automatique
def create_http_session() -> requests.Session:
    """Crée une session HTTP avec retry automatique."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,  # 1s, 2s, 4s entre les retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


# Session globale réutilisable
http_session = create_http_session()


def validate_url(url: str) -> bool:
    """Valide qu'une URL est correcte et sécurisée."""
    try:
        parsed = urlparse(url)
        
        # Vérifier le scheme
        if parsed.scheme not in ('http', 'https'):
            logger.warning(f"Scheme non supporté: {parsed.scheme}")
            return False
        
        # Vérifier qu'il y a un netloc (domaine)
        if not parsed.netloc:
            logger.warning("URL sans domaine")
            return False
        
        # Bloquer les adresses locales en production
        blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
        if parsed.hostname in blocked_hosts:
            logger.warning(f"Host bloqué: {parsed.hostname}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur validation URL: {e}")
        return False


def fetch_ical(url: str) -> Optional[str]:
    """
    Télécharge le contenu d'un calendrier iCal depuis une URL.
    
    Args:
        url: URL du fichier iCal
        
    Returns:
        Contenu du fichier iCal ou None en cas d'erreur
    """
    if not validate_url(url):
        logger.error(f"URL invalide: {url}")
        return None
    
    try:
        logger.debug(f"Téléchargement: {url}")
        
        response = http_session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "AirbnBook/1.0",
                "Accept": "text/calendar, application/ics, */*"
            }
        )
        
        response.raise_for_status()
        
        # Vérifier la taille (max 10 MB)
        content_length = len(response.content)
        max_size = 10 * 1024 * 1024
        
        if content_length > max_size:
            logger.error(f"Fichier trop volumineux: {content_length} bytes")
            return None
        
        logger.debug(f"Téléchargé {content_length} bytes")
        return response.text
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout lors du téléchargement: {url}")
        return None
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion: {e}")
        return None
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erreur HTTP {e.response.status_code}: {url}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur requête: {type(e).__name__}: {e}")
        return None


def sync_calendar(calendar_id: str, name: str, url: str) -> Dict[str, Any]:
    """
    Synchronise un calendrier individuel.
    
    Args:
        calendar_id: ID unique du calendrier
        name: Nom du calendrier
        url: URL du fichier iCal
        
    Returns:
        Dictionnaire avec le statut de synchronisation
    """
    result = {
        "calendar_id": calendar_id,
        "calendar_name": name,
        "success": False,
        "events_count": 0,
        "error_message": None,
        "synced_at": datetime.now(timezone.utc)
    }
    
    logger.info(f"Synchronisation du calendrier: {name} ({calendar_id})")
    
    # Télécharger le contenu
    ical_content = fetch_ical(url)
    
    if ical_content is None:
        result["error_message"] = "Échec du téléchargement"
        return result
    
    # Parser le contenu
    events = parse_ical(ical_content, calendar_id)
    
    result["success"] = True
    result["events_count"] = len(events)
    result["events"] = events
    
    logger.info(f"Calendrier {name}: {len(events)} événements synchronisés")
    
    return result


def sync_all_calendars(calendars: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Synchronise tous les calendriers.
    
    Args:
        calendars: Liste des calendriers à synchroniser
        
    Returns:
        Liste des résultats de synchronisation
    """
    results = []
    
    logger.info(f"Début de la synchronisation de {len(calendars)} calendrier(s)")
    start_time = time.time()
    
    for calendar in calendars:
        try:
            result = sync_calendar(
                calendar_id=calendar.get("id", ""),
                name=calendar.get("name", "Inconnu"),
                url=calendar.get("url", "")
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"Erreur inattendue pour {calendar.get('name')}: {e}")
            results.append({
                "calendar_id": calendar.get("id", ""),
                "calendar_name": calendar.get("name", "Inconnu"),
                "success": False,
                "events_count": 0,
                "error_message": str(e),
                "synced_at": datetime.now(timezone.utc)
            })
    
    elapsed = time.time() - start_time
    success_count = sum(1 for r in results if r["success"])
    
    logger.info(
        f"Synchronisation terminée: {success_count}/{len(calendars)} réussis "
        f"en {elapsed:.2f}s"
    )
    
    return results
