from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

# Indique explicitement le calendrier partagé
calendar_id = os.getenv('GOOGLE_CALENDAR_ID')

service = build('calendar', 'v3', credentials=credentials)

# Créer un événement
event = {
    'summary': 'Entraînement',
    'start': {'dateTime': datetime.datetime.now().isoformat(), 'timeZone': 'Europe/Paris'},
    'end': {'dateTime': (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(), 'timeZone': 'Europe/Paris'},
}

created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
print("Événement créé :", created_event.get('htmlLink'))

