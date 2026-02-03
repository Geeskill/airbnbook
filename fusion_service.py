import os
import re
import asyncio
import logging
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
import httpx
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

# ---------- ICS utils ----------
def parse_events(ics_text: str) -> List[str]:
    """Parse les événements d'un fichier ICS."""
    evts, cur, inside = [], [], False
    for raw in ics_text.splitlines():
        line = raw.rstrip("\r")
        u = line.strip().upper()
        if u == "BEGIN:VEVENT":
            inside, cur = True, ["BEGIN:VEVENT"]
        elif u == "END:VEVENT":
            cur.append("END:VEVENT")
            evts.append("\n".join(cur))
            inside = False
        elif inside:
            cur.append(line)
    return evts

def key_for(evt: str) -> str:
    """Génère une clé unique pour un événement."""
    uid = re.search(r"^UID:(.+)$", evt, flags=re.MULTILINE)
    if uid:
        return f"UID::{uid.group(1).strip()}"
    dt = re.search(r"^DTSTART[^:]*:(.+)$", evt, flags=re.MULTILINE)
    sm = re.search(r"^SUMMARY:(.+)$", evt, flags=re.MULTILINE)
    return f"DS::{dt.group(1).strip() if dt else ''}::SM::{sm.group(1).strip() if sm else ''}"

def merge_ics(airbnb_ics: str, booking_ics: str) -> str:
    """Fusionne deux calendriers ICS."""
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AirBnBook Fusion//ICS//FR",
        "CALSCALE:GREGORIAN",
    ]
    seen = {}
    for src, origin in [(airbnb_ics or "", "A"), (booking_ics or "", "B")]:
        for evt in parse_events(src):
            k = key_for(evt)
            if k not in seen:
                seen[k] = (origin, evt)
            elif seen[k][0] != "A" and origin == "A":
                seen[k] = (origin, evt)
    body = [v[1] for v in seen.values()]
    footer = ["END:VCALENDAR"]
    return "\n".join(header + body + footer) + "\n"

async def fetch(url: str) -> str:
    """Récupère un fichier ICS depuis une URL."""
    if not url:
        return ""
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de {url}: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de {url}")

# ---------- Endpoints ----------
@app.get("/healthz")
async def healthz():
    """Vérifie l'état du service."""
    return {
        "ok": True,
        "airbnb": bool(config.AIRBNB_ICS),
        "booking": bool(config.BOOKING_ICS),
        "outfile": config.OUTFILE,
    }

@app.post("/sync")
async def sync():
    """Synchronise les calendriers."""
    if not config.AIRBNB_ICS and not config.BOOKING_ICS:
        logger.error("Aucune URL source fournie.")
        raise HTTPException(status_code=400, detail="Aucune URL source fournie.")

    try:
        a_text, b_text = await asyncio.gather(
            fetch(config.AIRBNB_ICS),
            fetch(config.BOOKING_ICS)
        )
        merged = merge_ics(a_text, b_text)
        os.makedirs(os.path.dirname(config.OUTFILE), exist_ok=True)
        with open(config.OUTFILE, "w", encoding="utf-8") as f:
            f.write(merged)
        logger.info(f"Fichier fusionné écrit dans {config.OUTFILE}")
        return {"written": config.OUTFILE, "bytes": len(merged)}
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export")
async def export():
    """Exporte le calendrier fusionné."""
    if not os.path.exists(config.OUTFILE):
        logger.error("Fichier non trouvé. Lancez /sync d'abord.")
        raise HTTPException(status_code=404, detail="Fichier non trouvé. Lancez /sync d'abord.")
    with open(config.OUTFILE, "r", encoding="utf-8") as f:
        ics = f.read()
    return Response(content=ics, media_type="text/calendar; charset=utf-8")
