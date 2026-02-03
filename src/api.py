"""API REST FastAPI pour AirbnBook."""

import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from config import APP_NAME, APP_VERSION, API_KEY
from logger import logger
from models import (
    CalendarCreate,
    CalendarResponse,
    EventResponse,
    SyncStatus,
    HealthResponse
)
from storage import storage
from sync_service import sync_calendar, sync_all_calendars


# === Application FastAPI ===

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="API de synchronisation de calendriers iCal pour locations",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Heure de démarrage pour l'uptime
START_TIME = time.time()

# === Middleware CORS ===

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Authentification ===

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    """Vérifie la clé API si configurée."""
    if API_KEY is None:
        return True  # Pas d'auth requise
    
    if api_key is None or api_key != API_KEY:
        logger.warning(f"Tentative d'accès avec clé invalide")
        raise HTTPException(
            status_code=403,
            detail="Clé API invalide ou manquante"
        )
    
    return True


# === Routes Health ===

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Vérifie l'état de l'application."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        uptime_seconds=time.time() - START_TIME
    )


# === Routes Calendriers ===

@app.get(
    "/calendars",
    response_model=List[CalendarResponse],
    tags=["Calendriers"],
    dependencies=[Depends(verify_api_key)]
)
async def get_calendars():
    """Récupère la liste de tous les calendriers."""
    calendars = storage.get_all_calendars()
    return calendars


@app.post(
    "/calendars",
    response_model=CalendarResponse,
    status_code=201,
    tags=["Calendriers"],
    dependencies=[Depends(verify_api_key)]
)
async def create_calendar(calendar: CalendarCreate):
    """Crée un nouveau calendrier."""
    logger.info(f"Création calendrier: {calendar.name}")
    
    new_calendar = storage.add_calendar(
        name=calendar.name,
        url=str(calendar.url)
    )
    
    return new_calendar


@app.get(
    "/calendars/{calendar_id}",
    response_model=CalendarResponse,
    tags=["Calendriers"],
    dependencies=[Depends(verify_api_key)]
)
async def get_calendar(calendar_id: str):
    """Récupère un calendrier par son ID."""
    calendar = storage.get_calendar(calendar_id)
    
    if calendar is None:
        raise HTTPException(status_code=404, detail="Calendrier non trouvé")
    
    return calendar


@app.delete(
    "/calendars/{calendar_id}",
    status_code=204,
    tags=["Calendriers"],
    dependencies=[Depends(verify_api_key)]
)
async def delete_calendar(calendar_id: str):
    """Supprime un calendrier."""
    success = storage.delete_calendar(calendar_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Calendrier non trouvé")
    
    return None


# === Routes Synchronisation ===

@app.post(
    "/calendars/{calendar_id}/sync",
    response_model=SyncStatus,
    tags=["Synchronisation"],
    dependencies=[Depends(verify_api_key)]
)
async def sync_single_calendar(calendar_id: str):
    """Synchronise un calendrier spécifique."""
    calendar = storage.get_calendar(calendar_id)
    
    if calendar is None:
        raise HTTPException(status_code=404, detail="Calendrier non trouvé")
    
    result = sync_calendar(
        calendar_id=calendar["id"],
        name=calendar["name"],
        url=calendar["url"]
    )
    
    # Sauvegarder les événements si succès
    if result["success"] and "events" in result:
        storage.save_events(calendar_id, result["events"])
        del result["events"]  # Ne pas retourner tous les événements
    
    return SyncStatus(**result)


@app.post(
    "/sync",
    response_model=List[SyncStatus],
    tags=["Synchronisation"],
    dependencies=[Depends(verify_api_key)]
)
async def sync_all():
    """Synchronise tous les calendriers."""
    calendars = storage.get_all_calendars()
    
    if not calendars:
        return []
    
    results = sync_all_calendars(calendars)
    
    # Sauvegarder les événements pour chaque calendrier
    for result in results:
        if result["success"] and "events" in result:
            storage.save_events(result["calendar_id"], result["events"])
            del result["events"]
    
    return [SyncStatus(**r) for r in results]


# === Routes Événements ===

@app.get(
    "/events",
    response_model=List[EventResponse],
    tags=["Événements"],
    dependencies=[Depends(verify_api_key)]
)
async def get_events(
    calendar_id: Optional[str] = Query(None, description="Filtrer par calendrier"),
    start: Optional[datetime] = Query(None, description="Date de début"),
    end: Optional[datetime] = Query(None, description="Date de fin")
):
    """Récupère les événements avec filtres optionnels."""
    
    if start and end:
        events = storage.get_events_in_range(start, end, calendar_id)
    else:
        events = storage.get_events(calendar_id)
    
    return events


@app.get(
    "/calendars/{calendar_id}/events",
    response_model=List[EventResponse],
    tags=["Événements"],
    dependencies=[Depends(verify_api_key)]
)
async def get_calendar_events(calendar_id: str):
    """Récupère les événements d'un calendrier spécifique."""
    calendar = storage.get_calendar(calendar_id)
    
    if calendar is None:
        raise HTTPException(status_code=404, detail="Calendrier non trouvé")
    
    return storage.get_events(calendar_id)
