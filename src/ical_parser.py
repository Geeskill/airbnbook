"""Parser pour les fichiers iCalendar."""

from datetime import datetime, timezone, date
from typing import List, Dict, Any, Optional
from icalendar import Calendar

from logger import logger


def safe_get(component, key: str, default: str = "") -> str:
    """Récupère une valeur de composant de manière sécurisée."""
    value = component.get(key)
    if value is None:
        return default
    return str(value).strip()


def parse_datetime(component, key: str) -> Optional[datetime]:
    """Parse une date/heure depuis un composant iCal."""
    prop = component.get(key)
    
    if prop is None:
        return None
    
    dt = prop.dt
    
    # Si c'est une date sans heure, convertir en datetime
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    
    # Convertir en UTC si timezone-aware
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        try:
            return dt.astimezone(timezone.utc)
        except Exception as e:
            logger.warning(f"Erreur conversion timezone: {e}")
            return dt.replace(tzinfo=None)
    
    return dt


def validate_ical_content(content: str) -> bool:
    """Valide que le contenu ressemble à un fichier iCal."""
    if not content or not isinstance(content, str):
        return False
    
    content_stripped = content.strip()
    
    # Vérifications basiques du format iCal
    if not content_stripped.startswith("BEGIN:VCALENDAR"):
        return False
    
    if "END:VCALENDAR" not in content_stripped:
        return False
    
    return True


def parse_ical(ical_content: str, calendar_id: str = "") -> List[Dict[str, Any]]:
    """
    Parse le contenu d'un fichier iCalendar et retourne une liste d'événements.
    
    Args:
        ical_content: Contenu du fichier iCal en string
        calendar_id: ID du calendrier source
        
    Returns:
        Liste de dictionnaires représentant les événements
    """
    events = []
    
    # Validation du contenu
    if not validate_ical_content(ical_content):
        logger.error("Contenu iCal invalide ou vide")
        return events
    
    try:
        cal = Calendar.from_ical(ical_content)
    except ValueError as e:
        logger.error(f"Erreur de parsing iCal (format invalide): {e}")
        return events
    except Exception as e:
        logger.error(f"Erreur inattendue lors du parsing iCal: {type(e).__name__}: {e}")
        return events
    
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        
        try:
            event = parse_event(component, calendar_id)
            if event:
                events.append(event)
        except Exception as e:
            uid = safe_get(component, "UID", "inconnu")
            logger.warning(f"Erreur parsing événement (UID: {uid}): {e}")
            continue
    
    logger.info(f"Parsé {len(events)} événements depuis le calendrier {calendar_id}")
    return events


def parse_event(component, calendar_id: str) -> Optional[Dict[str, Any]]:
    """
    Parse un composant VEVENT individuel.
    
    Args:
        component: Composant iCal VEVENT
        calendar_id: ID du calendrier source
        
    Returns:
        Dictionnaire de l'événement ou None si invalide
    """
    # UID est obligatoire
    uid = safe_get(component, "UID")
    if not uid:
        logger.warning("Événement sans UID ignoré")
        return None
    
    # Dates de début et fin
    start = parse_datetime(component, "DTSTART")
    end = parse_datetime(component, "DTEND")
    
    if start is None:
        logger.warning(f"Événement {uid} sans date de début ignoré")
        return None
    
    # Si pas de date de fin, utiliser la date de début
    if end is None:
        end = start
    
    # Construire l'événement
    event = {
        "uid": uid,
        "summary": safe_get(component, "SUMMARY", "Sans titre"),
        "description": safe_get(component, "DESCRIPTION"),
        "location": safe_get(component, "LOCATION"),
        "start": start,
        "end": end,
        "calendar_id": calendar_id,
        "status": safe_get(component, "STATUS", "CONFIRMED"),
        "created": parse_datetime(component, "CREATED"),
        "last_modified": parse_datetime(component, "LAST-MODIFIED"),
    }
    
    return event
