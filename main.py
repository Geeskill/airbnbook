import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.config import Config
from src.fusion_service import fusion_router
from src.convert_fr_service import translate_router
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/airbnbook.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI(
    title="AirbnBook API",
    description="API pour fusionner et traduire les calendriers Airbnb et Booking.com",
    version="1.0.0"
)

# Chargement de la configuration
config = Config()

# Montage des routeurs API
app.include_router(fusion_router, prefix="/api/fusion", tags=["Fusion"])
app.include_router(translate_router, prefix="/api/translate", tags=["Traduction"])

# Configuration des templates et fichiers statiques
templates = Jinja2Templates(directory="src/web/templates")
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.get("/", response_model=None)
async def home(request: Request):
    """Page d'accueil avec statut des services."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": config,
            "fusion_status": os.path.exists(config.OUTFILE),
            "translate_status": os.path.exists(config.OUTFILE_FR)
        }
    )

@app.get("/config", response_model=None)
async def config_page(request: Request):
    """Page de configuration."""
    return templates.TemplateResponse(
        "config.html",
        {
            "request": request,
            "config": config
        }
    )

@app.post("/config")
async def update_config(request: Request):
    """Met à jour la configuration."""
    form_data = await request.form()

    # Mise à jour des variables (à implémenter avec python-dotenv)
    # Exemple: Config.update_env(form_data)

    return templates.TemplateResponse(
        "config.html",
        {
            "request": request,
            "config": config,
            "message": "Configuration mise à jour avec succès!"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.WEB_PORT,
        reload=True,
        log_config=None
    )
