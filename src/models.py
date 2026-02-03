"""Modèles Pydantic pour la validation des données."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, validator


class CalendarCreate(BaseModel):
    """Modèle pour créer un calendrier."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nom du calendrier"
    )
    url: HttpUrl = Field(
        ...,
        description="URL du calendrier iCal"
    )
    
    @validator("name")
    def name_must_be_valid(cls, v):
        """Valide et nettoie le nom."""
        v = v.strip()
        if not v:
            raise ValueError("Le nom ne peut pas être vide")
        # Empêcher les caractères dangereux
        forbidden_chars = ['<', '>', '"', "'", '\\', '/', ';']
        if any(char in v for char in forbidden_chars):
            raise ValueError(f"Caractères interdits: {forbidden_chars}")
        return v


class CalendarResponse(BaseModel):
    """Modèle de réponse pour un calendrier."""
    
    id: str
    name: str
    url: str
    last_sync: Optional[datetime] = None
    event_count: int = 0


class EventResponse(BaseModel):
    """Modèle de réponse pour un événement."""
    
    uid: str
    summary: str
    description: str
    location: str
    start: datetime
    end: datetime
    calendar_id: str


class SyncStatus(BaseModel):
    """Modèle pour le statut de synchronisation."""
    
    calendar_id: str
    calendar_name: str
    success: bool
    events_count: int = 0
    error_message: Optional[str] = None
    synced_at: datetime


class HealthResponse(BaseModel):
    """Modèle pour le health check."""
    
    status: str
    version: str
    uptime_seconds: float
