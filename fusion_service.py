from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import httpx
import asyncio
import logging
import os
from src.config import Config
from src.utils import merge_ics, parse_events

fusion_router = APIRouter()

@fusion_router.get("/health", summary="Vérifie l'état du service")
async def health_check():
    """Vérifie l'état du service de fusion."""
    return {
        "status": "ok",
        "airbnb_url": Config.AIRBNB_ICS,
        "booking_url": Config.BOOKING_ICS,
        "output_file": Config.OUTFILE
    }

@fusion_router.post("/sync", summary="Fusionne les calendriers")
async def sync_calendars():
    """Fusionne les calendriers Airbnb et Booking.com."""
    if not Config.AIRBNB_ICS or not Config.BOOKING_ICS:
        raise HTTPException(
            status_code=400,
            detail="Les URLs des calendriers ne sont pas configurées."
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            airbnb_task = client.get(Config.AIRBNB_ICS)
            booking_task = client.get(Config.BOOKING_ICS)
            airbnb_resp, booking_resp = await asyncio.gather(airbnb_task, booking_task)

            airbnb_resp.raise_for_status()
            booking_resp.raise_for_status()

            merged_ics = merge_ics(airbnb_resp.text, booking_resp.text)

            # Création du répertoire si nécessaire
            os.makedirs(os.path.dirname(Config.OUTFILE), exist_ok=True)

            with open(Config.OUTFILE, "w", encoding="utf-8") as f:
                f.write(merged_ics)

            logging.info(f"Calendrier fusionné écrit dans {Config.OUTFILE}")
            return JSONResponse(
                content={
                    "status": "success",
                    "file": Config.OUTFILE,
                    "events_count": len(parse_events(merged_ics)),
                    "message": "Calendriers fusionnés avec succès"
                }
            )
    except httpx.HTTPStatusError as e:
        logging.error(f"Erreur HTTP lors de la récupération des calendriers: {str(e)}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Erreur lors de la récupération des calendriers: {str(e)}"
        )
    except Exception as e:
        logging.error(f"Erreur lors de la fusion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la fusion des calendriers: {str(e)}"
        )
