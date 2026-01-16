import streamlit as st
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from zoneinfo import ZoneInfo
import json
import os
from dotenv import load_dotenv
from mistralai import Mistral

# Charger les variables d'environnement
load_dotenv()

PARIS = ZoneInfo("Europe/Paris")

# =========================
# Google Calendar
# =========================
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
calendar_service = build('calendar', 'v3', credentials=credentials)

def get_events(start_date, end_date):
    start_iso = start_date.isoformat() + "T00:00:00Z"
    end_iso = end_date.isoformat() + "T23:59:59Z"
    events = calendar_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_iso,
        timeMax=end_iso,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events.get("items", [])

def parse_event_datetime(event_part):
    if "dateTime" in event_part:
        return datetime.datetime.fromisoformat(
            event_part["dateTime"].replace("Z", "+00:00")
        ).astimezone(PARIS)
    if "date" in event_part:
        return datetime.datetime.fromisoformat(event_part["date"] + "T00:00:00").replace(tzinfo=PARIS)
    raise ValueError("Événement sans date détecté")

def is_free(start, end, events):
    for e in events:
        e_start = parse_event_datetime(e["start"])
        e_end = parse_event_datetime(e["end"])
        if start < e_end and end > e_start:
            return False
    return True

def create_event(summary, start, end, description):
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Paris"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Paris"}
    }
    return calendar_service.events().insert(calendarId=CALENDAR_ID, body=event).execute()


# Convertir numéro de semaine + jour → vraie date
def find_day_date(start_date, week_number, day_name):
    days = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
    idx = days.index(day_name)

    week_start = start_date + datetime.timedelta(weeks=week_number - 1)
    return week_start + datetime.timedelta(days=idx)


# =========================
# UI
# =========================
st.title("🏃 Assistant d'entraînement intelligent")

objectif = st.selectbox("Objectif", ["10 km", "Semi-marathon (21 km)", "Marathon"])
nb_weeks = st.slider("Durée du plan", 3, 16, 8)
seances_semaine = st.slider("Séances par semaine", 2, 7, 4)
heures_pref = st.time_input("Heure préférée", datetime.time(18, 0))
jours_pref = st.multiselect("Jours préférés", 
    ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"],
    default=["Mardi","Jeudi","Samedi"]
)

# =========================
# GENERATION AI
# =========================

from mistralai import Mistral
import json

def generate_training_plan(objectif, nb_weeks, seances_semaine, jours_pref):

    prompt = f"""
    Crée un plan d'entraînement structuré pour un coureur.
    Objectif: {objectif}
    Durée: {nb_weeks} semaines
    Séances par semaine: {seances_semaine}
    Jours préférés: {jours_pref}

    Format JSON strict:
    {{
      "weeks": [
        {{
          "week_number": 1,
          "sessions": [
            {{
              "day": "Mardi",
              "type": "Fractionné",
              "duration_minutes": 60,
              "description": "15 min échauffement, 5 fois 10min à 4min55/km, recupération : 2min, 15min cool down."
            }}
          ]
        }}
      ]
    }}
    """
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        raise ValueError("MISTRAL_API_KEY doit être définie dans le fichier .env")
    
    model = "mistral-small"

    client = Mistral(api_key=api_key)

    chat_response = client.chat.complete(
        model = model,
        messages = [
            {
                "role": "user",
                "content": prompt,
                
            },
        ],
        response_format={"type": "json_object"}
    )

    return chat_response.choices[0].message.content

def find_free_slot(preferred_date, preferred_time, duration_minutes, events, search_range_hours=2):
    """
    Cherche un créneau libre autour de l'heure préférée, sinon le lendemain.
    - preferred_date : date de la séance
    - preferred_time : heure préférée (datetime.time)
    - duration_minutes : durée de la séance
    - events : liste des événements existants
    - search_range_hours : nombre d'heures avant/après l'heure préférée à tester
    """
    start_dt = datetime.datetime.combine(preferred_date, preferred_time, tzinfo=PARIS)
    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

    # Vérifier autour de l'heure préférée
    for delta in range(search_range_hours + 1):
        for sign in [1, -1]:  # essayer après (+) puis avant (-)
            candidate_start = start_dt + datetime.timedelta(hours=sign * delta)
            candidate_end = candidate_start + datetime.timedelta(minutes=duration_minutes)
            if is_free(candidate_start, candidate_end, events):
                return candidate_start, candidate_end

    # Si pas trouvé sur ce jour, passer au jour suivant
    next_day = preferred_date + datetime.timedelta(days=1)
    return find_free_slot(next_day, preferred_time, duration_minutes, events, search_range_hours)



if st.button("Générer le plan et l'ajouter dans le calendrier"):
    raw = generate_training_plan(objectif, nb_weeks, seances_semaine, jours_pref)
    plan = json.loads(raw)

    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(weeks=nb_weeks)
    events = get_events(start_date, end_date)

    for week in plan["weeks"]:
        for session in week["sessions"]:
            day_name = session["day"]
            description = session["description"]
            duration = session["duration_minutes"]

            # Convertir le jour en date
            date = find_day_date(start_date, week["week_number"], day_name)

            # Chercher un créneau libre flexible
            start, end = find_free_slot(date, heures_pref, duration, events)

            # Créer l'événement
            create_event(
                summary=session["type"],
                start=start,
                end=end,
                description=description
            )


    st.success("✅ Plan complet ajouté dans ton Google Calendar")
