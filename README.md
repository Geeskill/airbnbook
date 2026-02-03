# **AirbnBook** 📅✨
**Synchronisation intelligente des calendriers Airbnb & Booking.com avec API REST**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.2-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/votre-utilisateur/airbnbook/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/votre-utilisateur/airbnbook.svg?style=social)](https://github.com/votre-utilisateur/airbnbook)

---

## **🚀 Présentation**
**AirbnBook** est un outil open-source qui permet de :
✅ **Fusionner automatiquement** les calendriers de réservation d'**Airbnb** et **Booking.com**
✅ **Traduire les libellés** en français (ex: *"Reserved"* → *"Airbnb (Réservation)"*)
✅ **Gérer via une API REST** ou une interface web intuitive
✅ **Exporter au format ICS** pour import dans Google Calendar, Apple Calendar, etc.

### **✨ Fonctionnalités clés**
| Fonctionnalité | Description |
|---------------|------------|
| **Fusion des calendriers** | Combine les disponibilités des deux plateformes en un seul fichier `.ics` |
| **Traduction automatique** | Convertit les libellés anglais en français |
| **API RESTful** | Endpoints pour synchroniser, traduire et exporter via requêtes HTTP |
| **Interface web** | Tableau de bord pour configurer et contrôler les services |
| **Système de logs** | Suivi des synchronisations et détection des erreurs |
| **Configuration flexible** | Personnalisation via `.env` ou interface web |
| **Export ICS** | Téléchargement du calendrier unifié |

---

## **🔧 Installation**

### **1️⃣ Prérequis**
- Python 3.8+
- pip
- Git
- Compte Airbnb et Booking.com avec accès aux URLs des calendriers

```bash
# Mettre à jour les paquets
apt update && apt upgrade -y

# Installer Python 3 et pip (gestionnaire de paquets Python)
apt install -y python3 python3-pip python3-venv

# Vérifier l'installation
python3 --version  # Doit afficher Python 3.11.x
pip3 --version     # Doit afficher pip 23.x
```

### **2️⃣ Installation**
```bash
# Cloner le dépôt
git clone https://github.com/Geeskill/airbnbook.git
cd airbnbook

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### **3️⃣ Configuration**
Créez un fichier `.env` à la racine du projet :

```ini
# URLs des calendriers (à obtenir depuis Airbnb/Booking.com)
AIRBNB_ICS="https://www.airbnb.com/calendar/ical/12345.ics"
BOOKING_ICS="https://admin.booking.com/ical/67890.ics"

# Chemins des fichiers de sortie
OUTFILE="data/unique-export.ics"
OUTFILE_FR="data/unique-export-fr.ics"

# Port du serveur web
WEB_PORT=8080
```
Ou copiez depuis le .env.exemple

```bash
# Créer le fichier .env
cp .env.example .env

# Éditer le fichier .env avec vos URLs de calendriers
nano .env
```

---

## **🛠️ Utilisation**

### **1️⃣ Interface Web**
1. Lancez l'application :
```bash
python src/main.py
```
2. Accédez à [http://localhost:8080](http://localhost:8080)
3. **Pages disponibles** :
   - **Accueil** : Statut des services et actions rapides
   - **Configuration** : Modifier les URLs des calendriers

### **2️⃣ API REST**
#### **Endpoints disponibles**
| Endpoint | Méthode | Description | Exemple |
|----------|---------|-------------|---------|
| `/api/fusion/health` | GET | Vérifie l'état du service de fusion | `curl http://localhost:8080/api/fusion/health` |
| `/api/fusion/sync` | POST | Fusionne les calendriers | `curl -X POST http://localhost:8080/api/fusion/sync` |
| `/api/translate/health` | GET | Vérifie l'état du service de traduction | `curl http://localhost:8080/api/translate/health` |
| `/api/translate/sync` | POST | Traduit les libellés en français | `curl -X POST http://localhost:8080/api/translate/sync` |
| `/api/translate/export` | GET | Télécharge le calendrier traduit | `curl http://localhost:8080/api/translate/export --output calendrier.ics` |

#### **Exemple avec Python**
```python
import requests

# Fusionner les calendriers
response = requests.post("http://localhost:8080/api/fusion/sync")
print(response.json())

# Télécharger le calendrier traduit
with open("calendrier.ics", "wb") as f:
    f.write(requests.get("http://localhost:8080/api/translate/export").content)
```

### **3️⃣ Import dans un calendrier externe**
- **Google Calendar** :
  `Paramètres > Importer & exporter > Sélectionner le fichier .ics`
- **Apple Calendar** :
  `Fichier > Importer > Sélectionner le fichier .ics`
- **Outlook** :
  `Fichier > Ouvrir et exporter > Importer/Exporter > Importer un fichier iCalendar`

---

## **📂 Structure du projet**
```
airbnbook/
├── .env                    # Variables d'environnement
├── .gitignore              # Fichiers ignorés
├── LICENSE                 # Licence MIT
├── README.md               # Documentation
├── requirements.txt        # Dépendances Python
├── logs/                   # Logs des services
│   ├── airbnbook.log       # Logs principaux
│   └── errors.log          # Erreurs
├── data/                   # Fichiers de sortie
│   ├── unique-export.ics   # Calendrier fusionné
│   └── unique-export-fr.ics # Calendrier traduit
└── src/
    ├── __init__.py
    ├── config.py           # Gestion de la configuration
    ├── fusion_service.py   # Service de fusion (API)
    ├── convert_fr_service.py # Service de traduction (API)
    ├── utils.py            # Fonctions utilitaires
    ├── web/                # Interface web
    │   ├── templates/      # Templates HTML
    │   └── static/         # CSS/JS
    └── main.py             # Serveur principal
```

---

## **🔄 Workflow complet**
1. **Configuration** :
   - Définir les URLs des calendriers dans `.env` ou via l'interface web
2. **Synchronisation** :
   - Fusionner les calendriers avec `/api/fusion/sync`
3. **Traduction** :
   - Convertir les libellés avec `/api/translate/sync`
4. **Export** :
   - Télécharger le calendrier avec `/api/translate/export`
5. **Import** :
   - Importer le fichier `.ics` dans votre calendrier préféré

---

## **🛡️ Sécurité & Bonnes pratiques**
✅ **Ne partagez pas vos URLs de calendriers** (contiennent des tokens d'accès)
✅ **Utilisez `.env`** et ajoutez-le à `.gitignore`
✅ **Vérifiez les logs** (`logs/errors.log`) en cas de problème
✅ **Sauvegardez régulièrement** vos fichiers `.ics`
✅ **Limitez l'accès à l'API** en production (ajoutez une authentification)

---

## **📜 API Documentation (Swagger)**
L'API est documentée automatiquement par FastAPI :
- Accédez à [http://localhost:8080/docs](http://localhost:8080/docs) pour la documentation interactive (Swagger UI)
- Ou à [http://localhost:8080/redoc](http://localhost:8080/redoc) pour une documentation alternative

---

## **🤝 Contribution**
Les contributions sont les bienvenues ! Voici comment participer :

1. **Forkez** le dépôt
2. **Créez une branche** :
   ```bash
   git checkout -b feature/ma-nouvelle-fonctionnalite
   ```
3. **Committez** vos modifications :
   ```bash
   git commit -m "Ajout de ma fonctionnalité"
   ```
4. **Push** vers la branche :
   ```bash
   git push origin feature/ma-nouvelle-fonctionnalite
   ```
5. **Ouvrez une Pull Request**

### **📌 Idées d'améliorations**
- [ ] **Dockerisation** pour un déploiement facile
- [ ] **Authentification** (JWT/OAuth2) pour sécuriser l'API
- [ ] **Notifications** (email/Slack) en cas d'échec
- [ ] **Tests unitaires** avec `pytest`
- [ ] **Support multi-langues** (espagnol, allemand, etc.)

---

## **📜 Licence**
Ce projet est sous **licence MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## **🙌 Remerciements**
- **FastAPI** pour le framework backend
- **httpx** pour les requêtes HTTP asynchrones
- **Jinja2** pour le templating HTML
- **La communauté open-source** pour les outils utilisés

---

**⭐️ Si ce projet vous a été utile, n'hésitez pas à lui donner une étoile !** 🚀
