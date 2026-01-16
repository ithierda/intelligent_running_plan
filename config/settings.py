"""
Configuration settings for the training coach application
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PLANS_DIR = DATA_DIR / "plans"
USER_DATA_DIR = DATA_DIR / "user_data"
CACHE_DIR = DATA_DIR / "cache"

# Create directories if they don't exist
for directory in [DATA_DIR, PLANS_DIR, USER_DATA_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Credentials
GARMIN_EMAIL = os.getenv('GARMIN_EMAIL')
GARMIN_PASSWORD = os.getenv('GARMIN_PASSWORD')

# Google Calendar - Chemin complet vers le fichier
service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
GOOGLE_SERVICE_ACCOUNT_FILE = str(BASE_DIR / service_account_file) if not os.path.isabs(service_account_file) else service_account_file
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'ithier.da@gmail.com')

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY', '68qzNaL3yrajUeE7Aovr3MJIsoWGCq83')

OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')

# Application Settings
APP_NAME = "Coach d'Entraînement Intelligent"
APP_VERSION = "1.0.0"

# Training defaults
DEFAULT_SESSIONS_PER_WEEK = 4
DEFAULT_TRAINING_DAYS = [2, 4, 6, 7]  # Mardi, Jeudi, Samedi, Dimanche
DEFAULT_TRAINING_TIME = "18:00"

# Recovery score weights
RECOVERY_WEIGHTS = {
    'sleep': 0.35,
    'hrv': 0.25,
    'load': 0.20,
    'rhr': 0.10,
    'subjective': 0.10
}

# Adaptation thresholds
RECOVERY_THRESHOLDS = {
    'excellent': 85,     # >= 85: maintenir séance
    'good': 70,          # 70-84: maintenir avec surveillance
    'moderate': 55,      # 55-69: alléger 20-30%
    'poor': 40,          # 40-54: remplacer par endurance légère
    'very_poor': 0       # < 40: repos complet
}

# ACWR (Acute:Chronic Workload Ratio) thresholds
ACWR_OPTIMAL_MIN = 0.8
ACWR_OPTIMAL_MAX = 1.3
ACWR_CAUTION_MAX = 1.5

# Pace zones for semi-marathon sub 1:45 (target: 4:58/km)
# Based on VMA 17 km/h
SEMI_145_PACES = {
    'recovery': '6:15',          # < 75% FCmax
    'endurance': '6:00',         # 75-80% FCmax
    'tempo': '5:20',             # 80-85% FCmax (allure marathon)
    'threshold': '4:55',         # 87-92% FCmax (allure semi)
    'intervals': '3:30',         # 95-100% FCmax (VMA)
}

# Training zones (% of max HR)
HR_ZONES = {
    'Z1_recovery': (60, 70),
    'Z2_endurance': (70, 80),
    'Z3_tempo': (80, 87),
    'Z4_threshold': (87, 92),
    'Z5_vma': (92, 100),
}

# Cache settings
CACHE_GARMIN_HOURS = 1  # Mettre en cache les données Garmin pendant 1h
CACHE_WEATHER_HOURS = 3

# Timezone
TIMEZONE = "Europe/Paris"

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Streamlit config
STREAMLIT_CONFIG = {
    'page_title': APP_NAME,
    'page_icon': '🏃',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded'
}
