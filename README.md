# **AirbnBook** 📅✨
**Synchronisation intelligente des calendriers Airbnb & Booking.com**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.2-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/votre-utilisateur/airbnbook/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/votre-utilisateur/airbnbook.svg?style=social)](https://github.com/votre-utilisateur/airbnbook)

---

## **🚀 Présentation**
**AirbnBook** est un outil open-source qui permet de **fusionner automatiquement** les calendriers de réservation d'**Airbnb** et **Booking.com**, tout en traduisant les libellés en français pour une meilleure lisibilité.

### **✨ Fonctionnalités clés**
✅ **Fusion des calendriers** : Combine les disponibilités des deux plateformes en un seul fichier `.ics`.
✅ **Traduction automatique** : Convertit les libellés anglais en français (ex: *"Reserved"* → *"Airbnb (Réservation)"*).
✅ **Interface web intuitive** : Configuration et contrôle via un tableau de bord simple.
✅ **Système de logs avancé** : Suivi des synchronisations et détection des erreurs.
✅ **Configuration via `.env`** : Personnalisation facile des URLs et chemins de fichiers.
✅ **Export ICS** : Téléchargement du calendrier unifié pour import dans Google Calendar, Apple Calendar, etc.

---

## **🔧 Installation**

### **1️⃣ Prérequis**
- **Python 3.8+**
- **pip** (gestionnaire de paquets Python)
- **Git** (pour cloner le dépôt)

### **2️⃣ Cloner le dépôt**
```bash
git clone https://github.com/votre-utilisateur/airbnbook.git
cd airbnbook
```

### **3️⃣ Créer un environnement virtuel (recommandé)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### **4️⃣ Installer les dépendances**
```bash
pip install -r requirements.txt
```

### **5️⃣ Configurer les variables d'environnement**
Créez un fichier `.env` à la racine du projet et ajoutez vos URLs de calendriers :
```ini
# URLs des calendriers
AIRBNB_ICS="https://www.airbnb.com/calendar/ical/12345.ics"
BOOKING_ICS="https://admin.booking.com/ical/67890.ics"

# Chemins des fichiers de sortie
OUTFILE="/srv/data/unique-export.ics"
OUTFILE_FR="/srv/data/unique-export-fr.ics"

# Ports des services
WEB_PORT=8080
```

### **6️⃣ Lancer l'application**
```bash
python src/main.py
```
**Accès à l'interface web** : [http://localhost:8080](http://localhost:8080)

---

## **🛠️ Utilisation**

### **1️⃣ Configuration**
1. Accédez à la page **[Configuration](http://localhost:8080/config)**.
2. Entrez les **URLs des calendriers** Airbnb et Booking.com.
3. Définissez les **chemins des fichiers de sortie** (optionnel).
4. Cliquez sur **"Sauvegarder"**.

### **2️⃣ Synchronisation**
1. Retournez à la page **[Accueil](http://localhost:8080/)**.
2. Cliquez sur **"Synchroniser les calendriers"** pour fusionner les données.
3. Cliquez sur **"Traduire en français"** pour convertir les libellés.
4. Téléchargez le calendrier unifié avec **"Télécharger le calendrier"**.

### **3️⃣ Import dans un calendrier externe**
- **Google Calendar** : `Paramètres > Importer & exporter > Sélectionner le fichier .ics`.
- **Apple Calendar** : `Fichier > Importer > Sélectionner le fichier .ics`.
- **Outlook** : `Fichier > Ouvrir et exporter > Importer/Exporter > Importer un fichier iCalendar`.

---

## **📂 Structure du projet**
```
airbnbook/
├── .env                    # Variables d'environnement
├── .gitignore              # Fichiers ignorés par Git
├── LICENSE                 # Licence MIT
├── README.md               # Documentation
├── requirements.txt        # Dépendances Python
├── logs/                   # Dossier des logs
│   ├── airbnbook.log       # Logs principaux
│   └── errors.log          # Logs d'erreurs
├── src/
│   ├── __init__.py         # Initialisation du package
│   ├── config.py           # Chargement des variables d'environnement
│   ├── fusion_service.py   # Service de fusion des calendriers (API)
│   ├── convert_fr_service.py # Service de traduction (API)
│   ├── web/                # Interface web
│   │   ├── __init__.py
│   │   ├── templates/      # Templates HTML (Jinja2)
│   │   │   ├── base.html
│   │   │   ├── index.html
│   │   │   └── config.html
│   │   └── static/         # Fichiers statiques (CSS, JS)
│   │       └── style.css
│   └── main.py             # Point d'entrée principal (serveur FastAPI)
└── tests/                  # Tests unitaires (à venir)
```

---

## **📜 Logs & Débogage**
Les logs sont stockés dans le dossier `logs/` :
- **`airbnbook.log`** : Logs généraux (synchronisations, traductions).
- **`errors.log`** : Erreurs critiques (problèmes de connexion, fichiers manquants).

**Exemple de log :**
```log
2023-10-15 14:30:25,123 - __main__ - INFO - Fichier fusionné écrit dans /srv/data/unique-export.ics
2023-10-15 14:30:26,456 - __main__ - INFO - Fichier traduit écrit dans /srv/data/unique-export-fr.ics
```

---

## **🔄 Workflow typique**
1. **Configuration** → Définir les URLs des calendriers dans `.env` ou via l'interface web.
2. **Synchronisation** → Fusionner les calendriers avec `/fusion/sync`.
3. **Traduction** → Convertir les libellés en français avec `/translate/sync`.
4. **Export** → Télécharger le calendrier unifié avec `/translate/export`.
5. **Import** → Importer le fichier `.ics` dans Google Calendar, Apple Calendar, etc.

---

## **🛡️ Sécurité & Bonnes pratiques**
✅ **Ne partagez pas vos URLs de calendriers** (elles contiennent des tokens d'accès).
✅ **Utilisez un `.env` local** et ajoutez-le à `.gitignore`.
✅ **Vérifiez les logs** en cas d'erreur (`logs/errors.log`).
✅ **Sauvegardez régulièrement** vos fichiers `.ics`.

---

## **🤝 Contribution**
Les contributions sont les bienvenues ! Voici comment participer :
1. **Forkez** le dépôt.
2. **Créez une branche** (`git checkout -b feature/ma-nouvelle-fonctionnalité`).
3. **Committez** vos modifications (`git commit -m "Ajout de ma fonctionnalité"`).
4. **Push** vers la branche (`git push origin feature/ma-nouvelle-fonctionnalité`).
5. **Ouvrez une Pull Request**.

### **📌 Idées d'améliorations**
- [ ] **Dockerisation** : Conteneurisation de l'application pour un déploiement facile.
- [ ] **Notifications** : Envoi d'emails/Slack en cas d'échec de synchronisation.
- [ ] **Tests unitaires** : Ajout de tests avec `pytest`.
- [ ] **Support multi-langues** : Traduction dans d'autres langues (espagnol, allemand, etc.).
- [ ] **Planification automatique** : Synchronisation quotidienne via `cron`.

---

## **📜 Licence**
Ce projet est sous **licence MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## **🙌 Remerciements**
- **FastAPI** pour le framework backend ultra-rapide.
- **httpx** pour les requêtes HTTP asynchrones.
- **Jinja2** pour le templating HTML.
- **La communauté open-source** pour les outils et bibliothèques utilisés.

---

## **📬 Contact**
Pour toute question ou suggestion, n'hésitez pas à ouvrir une **issue** ou à me contacter :

---

**⭐️ Si ce projet vous a été utile, n'hésitez pas à lui donner une étoile !** 🚀
