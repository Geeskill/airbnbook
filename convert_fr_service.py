import os
import re
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from src.config import Config

app = FastAPI()
config = Config()

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/airbnbook.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def unfold(ics: str) -> str:
    """Déplie les lignes d'un fichier ICS."""
    lines = ics.splitlines()
    out = []
    for line in lines:
        if line.startswith(" "):
            if out:
                out[-1] += line[1:]
        else:
            out.append(line)
    return "\n".join(out)

def fold(ics: str, limit: int = 75) -> str:
    """Replie les lignes d'un fichier ICS."""
    out_lines = []
    for line in ics.splitlines():
        raw = line.encode("utf-8")
        if len(raw) <= limit:
            out_lines.append(line)
            continue
        start = 0
        while start < len(raw):
            chunk = raw[start:start+limit]
            text = chunk.decode("utf-8", errors="ignore")
            if start == 0:
                out_lines.append(text)
            else:
                out_lines.append(" " + text)
            start += len(chunk)
    return "\n".join(out_lines)

def normalize(s: str) -> str:
    """Normalise une chaîne de caractères."""
    return re.sub(r"\s+", " ", s).strip().lower()

def translate_summary(value: str) -> str:
    """Traduit un libellé en français."""
    v = normalize(value)
    if v == "airbnb (not available)":
        return "Airbnb (Date bloquée)"
    if v == "reserved":
        return "Airbnb (Réservation)"
    if v == "closed - not available":
        return "Booking (Réservation)"
    return value

def translate_ics_summary_only(ics_unfolded: str) -> str:
    """Traduit les libellés d'un fichier ICS."""
    out = []
    for line in ics_unfolded.splitlines():
        up = line.upper()
        if up.startswith("SUMMARY:") or up.startswith("SUMMARY;"):
            if ":" in line:
                k, v = line.split(":", 1)
                v2 = translate_summary(v)
                out.append(f"{k}:{v2}")
            else:
                out.append(line)
        else:
            out.append(line)
    return "\n".join(out)

@app.get("/healthz")
def healthz():
    """Vérifie l'état du service."""
    return {
        "ok": True,
        "infile_exists": os.path.exists(config.OUTFILE),
        "infile": config.OUTFILE,
        "outfile": config.OUTFILE_FR,
    }

@app.post("/sync")
def sync():
    """Traduit le calendrier fusionné."""
    if not os.path.exists(config.OUTFILE):
        logger.error(f"Source manquante: {config.OUTFILE}. Lancez d'abord /sync côté fusion.")
        raise HTTPException(status_code=404, detail=f"Source manquante: {config.OUTFILE}. Lancez d'abord /sync côté fusion.")

    try:
        with open(config.OUTFILE, "r", encoding="utf-8") as f:
            src = f.read()

        unfolded = unfold(src)
        translated = translate_ics_summary_only(unfolded)
        folded = fold(translated)

        os.makedirs(os.path.dirname(config.OUTFILE_FR), exist_ok=True)
        tmp = config.OUTFILE_FR + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(folded if folded.endswith("\n") else folded + "\n")
        os.replace(tmp, config.OUTFILE_FR)
        logger.info(f"Fichier traduit écrit dans {config.OUTFILE_FR}")
        return {"written": config.OUTFILE_FR, "bytes": os.path.getsize(config.OUTFILE_FR)}
    except Exception as e:
        logger.error(f"Erreur lors de la traduction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export")
def export():
    """Exporte le calendrier traduit."""
    if not os.path.exists(config.OUTFILE_FR):
        logger.error("Fichier FR introuvable. Lancez /sync.")
        raise HTTPException(status_code=404, detail="Fichier FR introuvable. Lancez /sync.")
    with open(config.OUTFILE_FR, "r", encoding="utf-8") as f:
        ics = f.read()
    return Response(content=ics, media_type="text/calendar; charset=utf-8")
