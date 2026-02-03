import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AIRBNB_ICS = os.getenv("AIRBNB_ICS", "")
    BOOKING_ICS = os.getenv("BOOKING_ICS", "")
    OUTFILE = os.getenv("OUTFILE", "/srv/data/unique-export.ics")
    OUTFILE_FR = os.getenv("OUTFILE_FR", "/srv/data/unique-export-fr.ics")
    FUSION_PORT = int(os.getenv("FUSION_PORT", 8000))
    TRANSLATE_PORT = int(os.getenv("TRANSLATE_PORT", 8001))
    WEB_PORT = int(os.getenv("WEB_PORT", 8080))
    LOG_DIR = os.getenv("LOG_DIR", "logs")
