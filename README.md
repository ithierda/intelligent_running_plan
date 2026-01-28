# 🏃 Coach d'Entraînement Intelligent

> Application Streamlit de coaching personnalisé pour sports d'endurance avec adaptation dynamique basée sur les données physiologiques et les contraintes de vie.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io)

---

## 📁 Deux Applications en Une

Ce projet contient **deux applications distinctes** :

### 1. **app.py** - Générateur de Plan avec IA
Application simple pour générer et ajouter automatiquement des séances d'entraînement dans Google Calendar en utilisant l'IA Mistral.

**Utilisation :**
```bash
streamlit run app.py
```

### 2. **ui/Home.py** - Coach Complet avec Interface
Application complète avec interface multi-pages pour un coaching personnalisé avancé.

**Utilisation :**
```bash
streamlit run ui/Home.py
```

---

## 🎯 Fonctionnalités Principales

### Application Complète (ui/Home.py)
- 🎯 Plan semi-marathon sub 1:45 (12 semaines, 4 séances/semaine)
- 📊 Calcul du score de récupération quotidien (sommeil, HRV, charge)
- 🧠 Adaptation intelligente : maintien, allégement, report ou annulation
- 📅 Intégration Google Calendar (détection créneaux libres)
- 🔗 Connexion Garmin Connect (sommeil, activités, métriques)
- 📈 Dashboard de progression

### Roadmap
- 🍎 Intégration Apple Health
- 🌦️ Prise en compte météo
- 🤖 Machine Learning
- 🍽️ Recommandations nutritionnelles

---

## 🏗️ Architecture

```
Project/
├── models/                  # Modèles de données (Pydantic)
│   ├── athlete.py          # Profil athlète
│   ├── session.py          # Séances d'entraînement
│   ├── metrics.py          # Métriques quotidiennes
│   └── training_plan.py    # Plan complet
├── core/                    # Logique métier
│   ├── plan_generator.py   # Génération plan sub 1:45
│   └── session_adapter.py  # Adaptation intelligente
├── services/                # Intégrations API
│   ├── garmin_api.py
│   ├── calendar_service.py
│   └── weather_api.py
├── ui/                      # Interface Streamlit
│   └── pages/
│       ├── 01_dashboard.py
│       ├── 02_plan.py
│       ├── 03_today.py
│       └── 04_settings.py
├── config/
│   └── settings.py          # Configuration
└── app.py                   # Point d'entrée
```

---

## 🚀 Installation et Configuration

### Prérequis

- Python 3.10+
- Compte Garmin Connect
- Compte Google (pour Calendar API)
- Compte Mistral AI (pour génération IA)

### 1. Installation

```bash
cd Project

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration Google Calendar

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un nouveau projet
3. Activer **Google Calendar API**
4. Créer un **Service Account** :
   - Aller dans "IAM & Admin" > "Service Accounts"
   - Créer un compte de service
   - Télécharger le fichier JSON des credentials
5. Renommer le fichier en `service_account.json` et le placer dans le dossier `Project/`
6. **Important** : Partager votre Google Calendar avec l'email du service account (avec droits "Modifier les événements")

### 3. Configuration Mistral AI

1. Créer un compte sur [Mistral AI](https://console.mistral.ai/)
2. Générer une clé API
3. L'ajouter dans le fichier `.env`

---

## 💻 Utilisation

### Application Simple (app.py)

Génération rapide de plan d'entraînement avec IA :

```bash
streamlit run app.py
```

1. Choisir votre objectif (10km, Semi, Marathon)
2. Définir le nombre de semaines
3. Sélectionner vos jours et horaires préférés
4. Cliquer sur "Générer le plan"
5. Les séances sont automatiquement ajoutées dans Google Calendar

### Application Complète (ui/Home.py)

Interface complète multi-pages :

```bash
streamlit run ui/Home.py
```

**Navigation :**
- 🏠 **Home** : Vue d'ensemble et démarrage
- 📊 **Dashboard** : Statistiques et progression
- 📅 **Plan** : Visualisation du plan d'entraînement
- 🎯 **Today** : Recommandation du jour (analyse récupération + adaptation)
- ⚙️ **Settings** : Configuration profil et connexions API

**Workflow typique :**
1. **Page Settings** : Créer votre profil (âge, poids, VMA, objectif)
2. **Page Plan** : Générer votre plan personnalisé
3. **Page Today** : Chaque jour, voir la recommandation adaptée
4. **Page Dashboard** : Suivre votre progression


---

3. **Page Dashboard** : Vue d'ensemble
   - Score de récupération du jour
   - Progression hebdomadaire
   - Statistiques générales

4. **Page Today** : Recommandation quotidienne
   - Séance du jour
   - Recommandation d'adaptation
   - Justification (score, sommeil, charge)

---

## 🧠 Logique d'adaptation

### Score de récupération (0-100)

```
score = 35% sommeil + 25% HRV + 20% charge + 10% FC repos + 10% ressenti
```

### Décisions

| Score | État | Action |
|-------|------|--------|
| 85-100 | Excellent | ✅ Maintenir séance |
| 70-84 | Bon | 👍 Maintenir + surveiller |
| 55-69 | Moyen | ⚠️ Alléger 20-30% |
| 40-54 | Faible | 🔄 Remplacer par endurance |
| 0-39 | Très faible | 🛑 Repos complet |

### Facteurs pris en compte

- **Sommeil** : Durée, qualité, phases (Garmin)
- **HRV** : Variabilité fréquence cardiaque
- **Charge** : ACWR (Acute:Chronic Workload Ratio)
- **FC repos** : Par rapport à la baseline
- **Calendrier** : Disponibilité dans l'agenda
- **Séquence** : Enchaînement des séances intenses

---

## 📊 Plan d'entraînement Sub 1:45

### Structure (12 semaines)

#### Phase 1 : Base aérobie (Sem 1-4)
- **Objectif** : Construire endurance
- **Volume** : 30-40 km/semaine
- **Séances** :
  - 1x Sortie longue (60-75min)
  - 1x Fartlek léger
  - 2x Endurance fondamentale

#### Phase 2 : Développement (Sem 5-9)
- **Objectif** : VMA et allure semi
- **Volume** : 40-50 km/semaine
- **Séances** :
  - 1x VMA (ex: 10x400m à 3:30/km)
  - 1x Seuil (ex: 3x10min à 4:55/km)
  - 1x Sortie longue progressive
  - 1x Endurance active

#### Phase 3 : Affûtage (Sem 10-12)
- **Objectif** : Fraîcheur et affûtage
- **Volume** : -30 à -50%
- **Séances** : Volume réduit, intensité maintenue

### Allures cibles (pour 1:45 = 4:58/km)

| Zone | Allure | % FCmax | Usage |
|------|--------|---------|-------|
| Récupération | 6:15-6:30 | 70-75% | Décrassage |
| Endurance | 6:00-6:15 | 75-80% | Base aérobie |
| Tempo | 5:15-5:25 | 80-87% | Allure marathon |
| Seuil | 4:55-5:00 | 87-92% | **Allure semi** |
| VMA | 3:30-3:40 | 95-100% | Intervalles |

---

## 🔌 APIs utilisées

### Garmin Connect (`garminconnect` library)

```python
from garminconnect import Garmin

client = Garmin(email, password)
client.login()

# Récupérer données
activities = client.get_activities(0, 10)
sleep = client.get_sleep_data(date)
stats = client.get_stats(date)
```

**Données disponibles** :
- Activités (distance, allure, FC, cadence)
- Sommeil (durée, qualité, phases)
- Body Battery
- VO2 Max, VFC, FC repos
- Charge d'entraînement

### Google Calendar API

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

credentials = service_account.Credentials.from_service_account_file(
    'service_account.json'
)
service = build('calendar', 'v3', credentials=credentials)

# Récupérer événements
events = service.events().list(
    calendarId='primary',
    timeMin=start,
    timeMax=end
).execute()
```


*Bon entraînement ! 🏃‍♂️💨*
