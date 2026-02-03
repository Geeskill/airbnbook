import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.fusion_service import app as fusion_app
from src.convert_fr_service import app as translate_app
from src.config import Config

app = FastAPI()
config = Config()

# Montage des sous-applications
app.mount("/fusion", fusion_app)
app.mount("/translate", translate_app)

# Configuration des templates et fichiers statiques
templates = Jinja2Templates(directory="src/web/templates")
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "config": config})

@app.get("/config")
async def config_page(request: Request):
    return templates.TemplateResponse("config.html", {"request": request, "config": config})

@app.post("/config")
async def update_config(request: Request):
    form_data = await request.form()
    # Mettre à jour le fichier .env (à implémenter)
    # Rediriger vers la page de configuration
    return templates.TemplateResponse("config.html", {"request": request, "config": config, "message": "Configuration mise à jour!"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.WEB_PORT)
