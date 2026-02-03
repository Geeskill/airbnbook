from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import logging
import os
from src.config import Config
from src.utils import translate_ics_summary_only, unfold, fold

translate_router = APIRouter()

@translate_router.get("/healthz", summary="Vérifie l'état du service")
async def health_check():
    """Vérifie l'état du service de traduction."""
    return {
        "status": "ok",
        "input_file": Config.OUTFILE,
        "output_file": Config.OUTFILE_FR
    }

@translate_router.post("/sync", summary="Traduit le calendrier")
async def translate_calendar():
    """Traduit les libellés du calendrier en français."""
    if not os.path.exists(Config.OUTFILE):
        raise HTTPException(
            status_code=404,
            detail=f"Le fichier fusionné {Config.OUTFILE} n'existe pas. Lancez d'abord /api/fusion/sync."
        )

    try:
        with open(Config.OUTFILE, "r", encoding="utf-8") as f:
            ics_content = f.read()

        unfolded = unfold(ics_content)
        translated = translate_ics_summary_only(unfolded)
        folded = fold(translated)

        # Création du répertoire si nécessaire
        os.makedirs(os.path.dirname(Config.OUTFILE_FR), exist_ok=True)

        with open(Config.OUTFILE_FR, "w", encoding="utf-8") as f:
            f.write(folded)

        logging.info(f"Calendrier traduit écrit dans {Config.OUTFILE_FR}")
        return JSONResponse(
            content={
                "status": "success",
                "file": Config.OUTFILE_FR,
                "message": "Calendrier traduit avec succès"
            }
        )
    except Exception as e:
        logging.error(f"Erreur lors de la traduction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la traduction: {str(e)}"
        )

@translate_router.get("/export", summary="Exporte le calendrier traduit")
async def export_calendar():
    """Exporte le calendrier traduit au format .ics."""
    if not os.path.exists(Config.OUTFILE_FR):
        raise HTTPException(
            status_code=404,
            detail=f"Le fichier traduit {Config.OUTFILE_FR} n'existe pas. Lancez d'abord /api/translate/sync."
        )

    return FileResponse(
        Config.OUTFILE_FR,
        media_type="text/calendar",
        filename=os.path.basename(Config.OUTFILE_FR)
    )
