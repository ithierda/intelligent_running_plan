"""
Service Google Calendar
Gestion des événements d'entraînement dans Google Calendar
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, date, timedelta
from typing import Optional, List
import os
from dotenv import load_dotenv
from config.settings import GOOGLE_SERVICE_ACCOUNT_FILE

# Charger les variables d'environnement
load_dotenv()


class CalendarService:
    """Service pour interagir avec Google Calendar"""
    
    def __init__(self, calendar_id: Optional[str] = None):
        """
        Initialise le service Calendar
        
        Args:
            calendar_id: ID du calendrier (email). Si None, utilise GOOGLE_CALENDAR_ID de .env
        """
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        
        # Charger les credentials
        if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(
                f"Fichier service account introuvable: {GOOGLE_SERVICE_ACCOUNT_FILE}"
            )
        
        self.credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, 
            scopes=self.scopes
        )
        
        self.service = build('calendar', 'v3', credentials=self.credentials)
        self.calendar_id = calendar_id or os.getenv('GOOGLE_CALENDAR_ID', 'primary')
    
    def create_training_event(
        self,
        title: str,
        description: str,
        start_datetime: datetime,
        duration_minutes: int,
        location: Optional[str] = None
    ) -> dict:
        """
        Crée un événement d'entraînement
        
        Args:
            title: Titre de la séance
            description: Description détaillée
            start_datetime: Date et heure de début
            duration_minutes: Durée en minutes
            location: Lieu (optionnel)
            
        Returns:
            L'événement créé
        """
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        event = {
            'summary': f"🏃 {title}",
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'Europe/Paris',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'Europe/Paris',
            },
            'colorId': '4',  # Rouge pour sport
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'notification', 'minutes': 60},  # 1h avant
                    {'method': 'notification', 'minutes': 15},  # 15min avant
                ],
            },
        }
        
        if location:
            event['location'] = location
        
        created_event = self.service.events().insert(
            calendarId=self.calendar_id,
            body=event
        ).execute()
        
        return created_event
    
    def get_free_slots(
        self,
        start_date: date,
        end_date: date,
        min_duration_minutes: int = 60
    ) -> List[dict]:
        """
        Récupère les créneaux libres dans le calendrier
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            min_duration_minutes: Durée minimale du créneau
            
        Returns:
            Liste de créneaux libres {start, end}
        """
        # Convertir en datetime
        time_min = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
        time_max = datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z'
        
        # Récupérer les événements existants
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Définir les plages de recherche (par exemple 6h-22h chaque jour)
        free_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            # Plages potentielles : matin (6h-12h), midi (12h-14h), après-midi (14h-19h), soir (19h-22h)
            day_slots = [
                (datetime.combine(current_date, datetime.min.time().replace(hour=6)),
                 datetime.combine(current_date, datetime.min.time().replace(hour=12))),
                (datetime.combine(current_date, datetime.min.time().replace(hour=12)),
                 datetime.combine(current_date, datetime.min.time().replace(hour=14))),
                (datetime.combine(current_date, datetime.min.time().replace(hour=14)),
                 datetime.combine(current_date, datetime.min.time().replace(hour=19))),
                (datetime.combine(current_date, datetime.min.time().replace(hour=19)),
                 datetime.combine(current_date, datetime.min.time().replace(hour=22))),
            ]
            
            # Vérifier chaque créneau contre les événements existants
            for slot_start, slot_end in day_slots:
                is_free = True
                for event in events:
                    event_start = datetime.fromisoformat(
                        event['start'].get('dateTime', event['start'].get('date'))
                    )
                    event_end = datetime.fromisoformat(
                        event['end'].get('dateTime', event['end'].get('date'))
                    )
                    
                    # Vérifier chevauchement
                    if not (slot_end <= event_start or slot_start >= event_end):
                        is_free = False
                        break
                
                if is_free and (slot_end - slot_start).total_seconds() / 60 >= min_duration_minutes:
                    free_slots.append({
                        'start': slot_start,
                        'end': slot_end,
                        'duration_minutes': int((slot_end - slot_start).total_seconds() / 60)
                    })
            
            current_date += timedelta(days=1)
        
        return free_slots
    
    def check_availability(
        self,
        check_datetime: datetime,
        duration_minutes: int
    ) -> bool:
        """
        Vérifie si un créneau est disponible
        
        Args:
            check_datetime: Date et heure à vérifier
            duration_minutes: Durée nécessaire
            
        Returns:
            True si disponible, False sinon
        """
        end_datetime = check_datetime + timedelta(minutes=duration_minutes)
        
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=check_datetime.isoformat() + 'Z',
            timeMax=end_datetime.isoformat() + 'Z',
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        return len(events) == 0
    
    def delete_event(self, event_id: str) -> None:
        """Supprime un événement"""
        self.service.events().delete(
            calendarId=self.calendar_id,
            eventId=event_id
        ).execute()
    
    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        duration_minutes: Optional[int] = None
    ) -> dict:
        """
        Met à jour un événement existant
        
        Args:
            event_id: ID de l'événement
            title: Nouveau titre (optionnel)
            description: Nouvelle description (optionnel)
            start_datetime: Nouvelle date/heure (optionnel)
            duration_minutes: Nouvelle durée (optionnel)
            
        Returns:
            L'événement mis à jour
        """
        # Récupérer l'événement existant
        event = self.service.events().get(
            calendarId=self.calendar_id,
            eventId=event_id
        ).execute()
        
        # Mettre à jour les champs
        if title:
            event['summary'] = f"🏃 {title}"
        if description:
            event['description'] = description
        if start_datetime and duration_minutes:
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            event['start'] = {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'Europe/Paris',
            }
            event['end'] = {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'Europe/Paris',
            }
        
        # Envoyer la mise à jour
        updated_event = self.service.events().update(
            calendarId=self.calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        return updated_event


# Helper pour usage simple
def get_calendar_service(calendar_id: Optional[str] = None) -> CalendarService:
    """
    Retourne une instance du service Calendar
    
    Args:
        calendar_id: ID du calendrier (optionnel)
        
    Returns:
        Instance de CalendarService
    """
    return CalendarService(calendar_id)
