"""
utils.py - Fonctions utilitaires pour AirbnBook
Gère la fusion des calendriers, la traduction et le traitement des fichiers ICS.
"""

import re
import logging
from typing import List, Dict, Tuple
from icalendar import Calendar, Event
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Dictionnaire de traduction (anglais → français)
TRANSLATION_DICT = {
    "Reserved": "Réservé",
    "Booked": "Réservé",
    "Confirmed": "Confirmé",
    "Airbnb": "Airbnb",
    "Booking.com": "Booking.com",
    "Check-in": "Arrivée",
    "Check-out": "Départ",
    "Blocked": "Bloqué",
    "Not available": "Indisponible"
}

def unfold(ics_content: str) -> str:
    """
    Déplie les lignes d'un fichier ICS (supprime les sauts de ligne avec espaces).

    Args:
        ics_content (str): Contenu du fichier ICS

    Returns:
        str: Contenu déplié
    """
    return re.sub(r'\r?\n[ \t]', '', ics_content)

def fold(ics_content: str, line_length: int = 75) -> str:
    """
    Replie les lignes d'un fichier ICS selon la RFC 5545.

    Args:
        ics_content (str): Contenu du fichier ICS
        line_length (int): Longueur maximale des lignes

    Returns:
        str: Contenu replié
    """
    lines = []
    for line in ics_content.splitlines():
        if len(line) <= line_length:
            lines.append(line)
        else:
            # Découpage intelligent en respectant les mots
            words = line.split(';')
            current_line = words[0]
            for word in words[1:]:
                if len(current_line + ';' + word) <= line_length:
                    current_line += ';' + word
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
    return '\n'.join(lines)

def parse_events(ics_content: str) -> List[Dict]:
    """
    Parse un fichier ICS et extrait les événements.

    Args:
        ics_content (str): Contenu du fichier ICS

    Returns:
        List[Dict]: Liste des événements avec leurs propriétés
    """
    cal = Calendar.from_ical(ics_content)
    events = []

    for component in cal.walk():
        if component.name == "VEVENT":
            event = {
                "uid": str(component.get("uid")),
                "summary": str(component.get("summary")),
                "start": component.get("dtstart").dt,
                "end": component.get("dtend").dt,
                "description": str(component.get("description", "")),
                "location": str(component.get("location", "")),
                "source": "airbnb" if "airbnb" in str(component.get("url", "")).lower()
                          else "booking"
            }
            events.append(event)

    return events

def key_for(event: Dict) -> Tuple:
    """
    Génère une clé unique pour un événement (pour éviter les doublons).

    Args:
        event (Dict): Événement à traiter

    Returns:
        Tuple: Clé unique (start, end, summary)
    """
    return (event["start"], event["end"], event["summary"])

def merge_ics(airbnb_ics: str, booking_ics: str) -> str:
    """
    Fusionne deux fichiers ICS en un seul calendrier unifié.

    Args:
        airbnb_ics (str): Contenu du calendrier Airbnb
        booking_ics (str): Contenu du calendrier Booking.com

    Returns:
        str: Calendrier fusionné au format ICS
    """
    # Parse les deux calendriers
    airbnb_cal = Calendar.from_ical(airbnb_ics)
    booking_cal = Calendar.from_ical(booking_ics)

    # Crée un nouveau calendrier
    merged_cal = Calendar()
    merged_cal.add('prodid', '-//AirbnBook//Calendar Sync//FR')
    merged_cal.add('version', '2.0')

    # Dictionnaire pour éviter les doublons
    seen_events = {}

    # Ajoute les événements d'Airbnb
    for component in airbnb_cal.walk():
        if component.name == "VEVENT":
            event = {
                "uid": str(component.get("uid")),
                "summary": str(component.get("summary")),
                "start": component.get("dtstart").dt,
                "end": component.get("dtend").dt,
                "description": str(component.get("description", "")),
                "source": "airbnb"
            }
            key = key_for(event)
            if key not in seen_events:
                merged_cal.add_component(component)
                seen_events[key] = True

    # Ajoute les événements de Booking.com
    for component in booking_cal.walk():
        if component.name == "VEVENT":
            event = {
                "uid": str(component.get("uid")),
                "summary": str(component.get("summary")),
                "start": component.get("dtstart").dt,
                "end": component.get("dtend").dt,
                "description": str(component.get("description", "")),
                "source": "booking"
            }
            key = key_for(event)
            if key not in seen_events:
                # Modifie le summary pour indiquer la source
                original_summary = str(component.get("summary"))
                component["summary"] = f"Booking.com - {original_summary}"
                merged_cal.add_component(component)
                seen_events[key] = True

    return merged_cal.to_ical().decode('utf-8')

def translate_ics_summary_only(ics_content: str) -> str:
    """
    Traduit uniquement les champs "summary" d'un fichier ICS en français.

    Args:
        ics_content (str): Contenu du fichier ICS

    Returns:
        str: Contenu traduit
    """
    cal = Calendar.from_ical(ics_content)

    for component in cal.walk():
        if component.name == "VEVENT":
            original_summary = str(component.get("summary"))
            translated_summary = original_summary

            # Détection de la source
            if "airbnb" in str(component.get("url", "")).lower():
                translated_summary = f"Airbnb ({translate_text(original_summary)})"
            elif "booking" in original_summary.lower():
                translated_summary = f"Booking.com ({translate_text(original_summary.replace('Booking.com -', ''))})"
            else:
                translated_summary = translate_text(original_summary)

            component["summary"] = translated_summary

    return cal.to_ical().decode('utf-8')

def translate_text(text: str) -> str:
    """
    Traduit un texte de l'anglais vers le français en utilisant le dictionnaire.

    Args:
        text (str): Texte à traduire

    Returns:
        str: Texte traduit
    """
    # Remplace les mots connus
    for en, fr in TRANSLATION_DICT.items():
        text = re.sub(rf'\b{en}\b', fr, text, flags=re.IGNORECASE)

    # Cas particuliers
    if "airbnb" in text.lower():
        text = re.sub(r'airbnb', 'Airbnb', text, flags=re.IGNORECASE)
    if "booking" in text.lower():
        text = re.sub(r'booking', 'Booking.com', text, flags=re.IGNORECASE)

    return text

def validate_ics(ics_content: str) -> bool:
    """
    Valide la structure d'un fichier ICS.

    Args:
        ics_content (str): Contenu du fichier ICS

    Returns:
        bool: True si valide, False sinon
    """
    try:
        cal = Calendar.from_ical(ics_content)
        if not cal.get("prodid") or not cal.get("version"):
            return False
        return True
    except Exception as e:
        logger.error(f"Erreur de validation ICS: {str(e)}")
        return False
