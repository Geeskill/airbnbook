"""
api.py - API REST pour AirbnBook
Gestion des calendriers, synchronisation et export ICS.
"""

import re
import hashlib
from datetime import datetime, date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from icalendar import Calendar, Event

from src.config import Config
from src.logger import get_logger
from src.models import CalendarSource, CalendarEvent, SyncResult
from src.storage import Storage
from src.sync_service import SyncService

# Logger
logger = get_logger(__name__)

# Storage et Services
storage = Storage()
sync_service = SyncService(storage)

# Application FastAPI
app = FastAPI(
    title="AirbnBook API",
    description="API de synchronisation de calendriers Airbnb et Booking.com",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# SÉCURITÉ
# =============================================================================

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Vérifie la clé API si configurée."""
    if Config.API_KEY is None:
        return True
    
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Clé API manquante. Ajoutez le header 'X-API-Key'."
        )
    
    if x_api_key != Config.API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Clé API invalide."
        )
    
    return True


# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

class CalendarSourceCreate(BaseModel):
    """Modèle pour créer une source de calendrier."""
    name: str
    url: HttpUrl
    source_type: str  # "airbnb" ou "booking"
    property_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Appartement Paris",
                "url": "https://www.airbnb.com/calendar/ical/xxx.ics",
                "source_type": "airbnb",
                "property_name": "Studio Montmartre"
            }
        }


class CalendarSourceUpdate(BaseModel):
    """Modèle pour mettre à jour une source."""
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    source_type: Optional[str] = None
    property_name: Optional[str] = None


class ApiResponse(BaseModel):
    """Réponse API standard."""
    success: bool
    message: str
    data: Optional[dict] = None


# =============================================================================
# TRADUCTION FR
# =============================================================================

TRANSLATION_DICT = {
    "Reserved": "Réservé",
    "Booked": "Réservé",
    "Confirmed": "Confirmé",
    "Not available": "Indisponible",
    "Blocked": "Bloqué",
    "Check-in": "Arrivée",
    "Check-out": "Départ",
    "Unavailable": "Indisponible",
    "Closed": "Fermé",
}


def translate_text(text: str) -> str:
    """Traduit un texte en français."""
    if not text:
        return text
    
    result = text
    for en, fr in TRANSLATION_DICT.items():
        result = re.sub(rf'\b{re.escape(en)}\b', fr, result, flags=re.IGNORECASE)
    
    return result


# =============================================================================
# ROUTES - SANTÉ
# =============================================================================

@app.get("/", tags=["Santé"])
async def root():
    """Redirige vers l'interface web."""
    return FileResponse("src/web/index.html")


@app.get("/health", tags=["Santé"])
async def health_check():
    """Vérifie l'état de l'API."""
    sources = storage.get_sources()
    events = storage.get_events()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "sources_count": len(sources),
            "events_count": len(events)
        }
    }


@app.get("/api/health", tags=["Santé"])
async def api_health():
    """Alias pour /health."""
    return await health_check()


# =============================================================================
# ROUTES - SOURCES DE CALENDRIERS
# =============================================================================

@app.get("/api/sources", tags=["Sources"], response_model=List[dict])
async def list_sources():
    """Liste toutes les sources de calendriers."""
    sources = storage.get_sources()
    logger.info(f"Liste des sources: {len(sources)} trouvées")
    return sources


@app.get("/api/sources/{source_id}", tags=["Sources"])
async def get_source(source_id: str):
    """Récupère une source par son ID."""
    sources = storage.get_sources()
    
    for source in sources:
        if source.get("id") == source_id:
            return source
    
    raise HTTPException(status_code=404, detail=f"Source '{source_id}' non trouvée")


@app.post("/api/sources", tags=["Sources"], status_code=201)
async def create_source(source: CalendarSourceCreate, _: bool = Depends(verify_api_key)):
    """Crée une nouvelle source de calendrier."""
    # Validation du type
    if source.source_type not in ["airbnb", "booking"]:
        raise HTTPException(
            status_code=400,
            detail="source_type doit être 'airbnb' ou 'booking'"
        )
    
    # Générer un ID unique
    source_id = hashlib.md5(f"{source.name}{source.url}".encode()).hexdigest()[:12]
    
    # Vérifier si la source existe déjà
    existing = storage.get_sources()
    for s in existing:
        if s.get("url") == str(source.url):
            raise HTTPException(
                status_code=409,
                detail="Cette URL de calendrier existe déjà"
            )
    
    # Créer la source
    new_source = {
        "id": source_id,
        "name": source.name,
        "url": str(source.url),
        "source_type": source.source_type,
        "property_name": source.property_name,
        "created_at": datetime.now().isoformat(),
        "last_sync": None,
        "enabled": True
    }
    
    storage.add_source(new_source)
    logger.info(f"Source créée: {source.name} ({source_id})")
    
    return {
        "success": True,
        "message": "Source créée avec succès",
        "data": new_source
    }


@app.put("/api/sources/{source_id}", tags=["Sources"])
async def update_source(
    source_id: str,
    source: CalendarSourceUpdate,
    _: bool = Depends(verify_api_key)
):
    """Met à jour une source existante."""
    sources = storage.get_sources()
    
    for i, s in enumerate(sources):
        if s.get("id") == source_id:
            # Mise à jour des champs fournis
            if source.name is not None:
                sources[i]["name"] = source.name
            if source.url is not None:
                sources[i]["url"] = str(source.url)
            if source.source_type is not None:
                if source.source_type not in ["airbnb", "booking"]:
                    raise HTTPException(
                        status_code=400,
                        detail="source_type doit être 'airbnb' ou 'booking'"
                    )
                sources[i]["source_type"] = source.source_type
            if source.property_name is not None:
                sources[i]["property_name"] = source.property_name
            
            sources[i]["updated_at"] = datetime.now().isoformat()
            storage.save_sources(sources)
            
            logger.info(f"Source mise à jour: {source_id}")
            return {
                "success": True,
                "message": "Source mise à jour",
                "data": sources[i]
            }
    
    raise HTTPException(status_code=404, detail=f"Source '{source_id}' non trouvée")


@app.delete("/api/sources/{source_id}", tags=["Sources"])
async def delete_source(source_id: str, _: bool = Depends(verify_api_key)):
    """Supprime une source de calendrier."""
    sources = storage.get_sources()
    
    for i, s in enumerate(sources):
        if s.get("id") == source_id:
            deleted = sources.pop(i)
            storage.save_sources(sources)
            
            logger.info(f"Source supprimée: {source_id}")
            return {
                "success": True,
                "message": "Source supprimée",
                "data": deleted
            }
    
    raise HTTPException(status_code=404, detail=f"Source '{source_id}' non trouvée")


@app.post("/api/sources/{source_id}/toggle", tags=["Sources"])
async def toggle_source(source_id: str, _: bool = Depends(verify_api_key)):
    """Active/désactive une source."""
    sources = storage.get_sources()
    
    for i, s in enumerate(sources):
        if s.get("id") == source_id:
            sources[i]["enabled"] = not sources[i].get("enabled", True)
            storage.save_sources(sources)
            
            status = "activée" if sources[i]["enabled"] else "désactivée"
            logger.info(f"Source {source_id} {status}")
            
            return {
                "success": True,
                "message": f"Source {status}",
                "data": sources[i]
            }
    
    raise HTTPException(status_code=404, detail=f"Source '{source_id}' non trouvée")


# =============================================================================
# ROUTES - ÉVÉNEMENTS
# =============================================================================

@app.get("/api/events", tags=["Événements"])
async def list_events(
    source_type: Optional[str] = Query(None, description="Filtrer par type (airbnb/booking)"),
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500, description="Nombre max d'événements")
):
    """Liste tous les événements avec filtres optionnels."""
    events = storage.get_events()
    
    # Filtre par type de source
    if source_type:
        if source_type not in ["airbnb", "booking"]:
            raise HTTPException(
                status_code=400,
                detail="source_type doit être 'airbnb' ou 'booking'"
            )
        events = [e for e in events if e.get("source") == source_type]
    
    # Filtre par date de début
    if start_date:
        try:
            start = datetime.fromisoformat(start_date).date()
            events = [
                e for e in events
                if datetime.fromisoformat(e["start"]).date() >= start
            ]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Format de date invalide. Utilisez YYYY-MM-DD"
            )
    
    # Filtre par date de fin
    if end_date:
        try:
            end = datetime.fromisoformat(end_date).date()
            events = [
                e for e in events
                if datetime.fromisoformat(e["end"]).date() <= end
            ]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Format de date invalide. Utilisez YYYY-MM-DD"
            )
    
    # Tri par date de début
    events.sort(key=lambda e: e.get("start", ""))
    
    # Limite
    events = events[:limit]
    
    logger.info(f"Liste des événements: {len(events)} trouvés")
    
    return {
        "count": len(events),
        "events": events
    }


@app.get("/api/events/upcoming", tags=["Événements"])
async def upcoming_events(days: int = Query(30, ge=1, le=365)):
    """Récupère les événements des X prochains jours."""
    events = storage.get_events()
    today = date.today()
    end_date = today + timedelta(days=days)
    
    from datetime import timedelta
    
    upcoming = []
    for event in events:
        try:
            event_start = datetime.fromisoformat(event["start"]).date()
            if today <= event_start <= end_date:
                upcoming.append(event)
        except (ValueError, KeyError):
            continue
    
    upcoming.sort(key=lambda e: e.get("start", ""))
    
    return {
        "period": f"{today} - {end_date}",
        "count": len(upcoming),
        "events": upcoming
    }


@app.get("/api/events/stats", tags=["Événements"])
async def events_stats():
    """Statistiques sur les événements."""
    events = storage.get_events()
    sources = storage.get_sources()
    
    # Comptage par source
    by_source = {"airbnb": 0, "booking": 0, "other": 0}
    for event in events:
        source = event.get("source", "other")
        if source in by_source:
            by_source[source] += 1
        else:
            by_source["other"] += 1
    
    # Événements futurs
    today = date.today()
    future_events = [
        e for e in events
        if datetime.fromisoformat(e.get("start", "1970-01-01")).date() >= today
    ]
    
    return {
        "total_events": len(events),
        "future_events": len(future_events),
        "past_events": len(events) - len(future_events),
        "by_source": by_source,
        "sources_count": len(sources),
        "last_update": storage.get_last_sync()
    }


# =============================================================================
# ROUTES - SYNCHRONISATION
# =============================================================================

@app.post("/api/sync", tags=["Synchronisation"])
async def sync_all(
    force: bool = Query(False, description="Forcer la synchronisation"),
    _: bool = Depends(verify_api_key)
):
    """Synchronise tous les calendriers."""
    try:
        result = await sync_service.sync_all(force=force)
        
        logger.info(f"Synchronisation terminée: {result}")
        
        return {
            "success": True,
            "message": "Synchronisation terminée",
            "data": result
        }
    except Exception as e:
        logger.error(f"Erreur de synchronisation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la synchronisation: {str(e)}"
        )


@app.post("/api/sync/{source_id}", tags=["Synchronisation"])
async def sync_source(source_id: str, _: bool = Depends(verify_api_key)):
    """Synchronise une source spécifique."""
    sources = storage.get_sources()
    
    source = None
    for s in sources:
        if s.get("id") == source_id:
            source = s
            break
    
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' non trouvée")
    
    try:
        result = await sync_service.sync_source(source)
        
        logger.info(f"Source {source_id} synchronisée: {result}")
        
        return {
            "success": True,
            "message": f"Source '{source['name']}' synchronisée",
            "data": result
        }
    except Exception as e:
        logger.error(f"Erreur sync source {source_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )


@app.get("/api/sync/status", tags=["Synchronisation"])
async def sync_status():
    """Statut de la dernière synchronisation."""
    last_sync = storage.get_last_sync()
    sources = storage.get_sources()
    
    sources_status = []
    for source in sources:
        sources_status.append({
            "id": source.get("id"),
            "name": source.get("name"),
            "enabled": source.get("enabled", True),
            "last_sync": source.get("last_sync"),
            "last_error": source.get("last_error")
        })
    
    return {
        "last_global_sync": last_sync,
        "sources": sources_status
    }


# =============================================================================
# ROUTES - EXPORT ICS
# =============================================================================

def create_ics_calendar(events: List[dict], name: str, translate: bool = False) -> str:
    """Crée un calendrier ICS à partir des événements."""
    cal = Calendar()
    cal.add('prodid', '-//AirbnBook//Calendar Sync//FR')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', name)
    cal.add('x-wr-timezone', 'Europe/Paris')
    
    for event_data in events:
        try:
            event = Event()
            
            # UID
            uid = event_data.get('uid', hashlib.md5(
                f"{event_data.get('start')}{event_data.get('summary')}".encode()
            ).hexdigest())
            event.add('uid', uid)
            
            # Summary (avec traduction optionnelle)
            summary = event_data.get('summary', 'Réservation')
            source = event_data.get('source', '')
            
            if translate:
                summary = translate_text(summary)
                # Ajouter le préfixe source
                if source == 'airbnb':
                    summary = f"🏠 Airbnb - {summary}"
                elif source == 'booking':
                    summary = f"🏨 Booking - {summary}"
            
            event.add('summary', summary)
            
            # Dates
            start_str = event_data.get('start')
            end_str = event_data.get('end')
            
            if start_str:
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                event.add('dtstart', start_dt.date())
            
            if end_str:
                end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                event.add('dtend', end_dt.date())
            
            # Description
            description = event_data.get('description', '')
            if source:
                description = f"Source: {source.upper()}\n{description}".strip()
            if description:
                event.add('description', description)
            
            # Location
            location = event_data.get('location', '')
            if location:
                event.add('location', location)
            
            # Timestamp
            event.add('dtstamp', datetime.now())
            
            cal.add_component(event)
            
        except Exception as e:
            logger.warning(f"Erreur création événement ICS: {e}")
            continue
    
    return cal.to_ical().decode('utf-8')


@app.get("/export/calendar.ics", tags=["Export"])
async def export_calendar():
    """Exporte tous les événements au format ICS."""
    events = storage.get_events()
    
    if not events:
        raise HTTPException(
            status_code=404,
            detail="Aucun événement à exporter. Lancez d'abord une synchronisation."
        )
    
    ics_content = create_ics_calendar(
        events,
        name="AirbnBook - Calendrier unifié",
        translate=False
    )
    
    logger.info(f"Export ICS: {len(events)} événements")
    
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=airbnbook-calendar.ics",
            "Cache-Control": "no-cache"
        }
    )


@app.get("/export/calendar-fr.ics", tags=["Export"])
async def export_calendar_french():
    """Exporte le calendrier traduit en français."""
    events = storage.get_events()
    
    if not events:
        raise HTTPException(
            status_code=404,
            detail="Aucun événement à exporter. Lancez d'abord une synchronisation."
        )
    
    ics_content = create_ics_calendar(
        events,
        name="AirbnBook - Calendrier unifié (FR)",
        translate=True
    )
    
    logger.info(f"Export ICS FR: {len(events)} événements")
    
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=airbnbook-calendar-fr.ics",
            "Cache-Control": "no-cache"
        }
    )


@app.get("/export/airbnb.ics", tags=["Export"])
async def export_airbnb_only():
    """Exporte uniquement les événements Airbnb."""
    events = storage.get_events()
    airbnb_events = [e for e in events if e.get("source") == "airbnb"]
    
    if not airbnb_events:
        raise HTTPException(
            status_code=404,
            detail="Aucun événement Airbnb à exporter."
        )
    
    ics_content = create_ics_calendar(
        airbnb_events,
        name="AirbnBook - Airbnb",
        translate=True
    )
    
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=airbnbook-airbnb.ics",
            "Cache-Control": "no-cache"
        }
    )


@app.get("/export/booking.ics", tags=["Export"])
async def export_booking_only():
    """Exporte uniquement les événements Booking."""
    events = storage.get_events()
    booking_events = [e for e in events if e.get("source") == "booking"]
    
    if not booking_events:
        raise HTTPException(
            status_code=404,
            detail="Aucun événement Booking à exporter."
        )
    
    ics_content = create_ics_calendar(
        booking_events,
        name="AirbnBook - Booking",
        translate=True
    )
    
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=airbnbook-booking.ics",
            "Cache-Control": "no-cache"
        }
    )


# =============================================================================
# FICHIERS STATIQUES (Interface Web)
# =============================================================================

# Monter le dossier web pour les fichiers statiques
app.mount("/static", StaticFiles(directory="src/web"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon."""
    return FileResponse("src/web/favicon.ico")


# =============================================================================
# GESTION DES ERREURS
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Gestion des 404."""
    return Response(
        content='{"error": "Ressource non trouvée"}',
        status_code=404,
        media_type="application/json"
    )


@app.exception_handler(500)
async def server_error_handler(request, exc):
    """Gestion des erreurs serveur."""
    logger.error(f"Erreur serveur: {exc}")
    return Response(
        content='{"error": "Erreur interne du serveur"}',
        status_code=500,
        media_type="application/json"
    )
