"""
Modèle de données pour le plan d'entraînement complet
"""
from pydantic import BaseModel, Field
from datetime import date, timedelta
from typing import Optional
from enum import Enum
from .session import TrainingSession, SessionType


class TrainingPhase(str, Enum):
    """Phases d'un plan d'entraînement"""
    BASE = "Base aérobie"
    BUILD = "Développement"
    PEAK = "Pic/Intensification"
    TAPER = "Affûtage"
    RECOVERY = "Récupération"
    RACE = "Course"


class WeekType(str, Enum):
    """Types de semaine"""
    NORMAL = "Normale"
    RECOVERY = "Récupération"
    PEAK = "Pic"
    RACE = "Course"


class TrainingWeek(BaseModel):
    """Une semaine d'entraînement"""
    week_number: int = Field(..., ge=1, description="Numéro de la semaine")
    start_date: date = Field(..., description="Date de début (lundi)")
    end_date: date = Field(..., description="Date de fin (dimanche)")
    
    phase: TrainingPhase
    week_type: WeekType = Field(default=WeekType.NORMAL)
    
    sessions: list[TrainingSession] = Field(default_factory=list)
    
    # Métriques de la semaine
    target_volume_km: Optional[float] = Field(None, description="Volume cible en km")
    target_duration_minutes: Optional[int] = Field(None, description="Durée totale cible")
    target_elevation_gain_m: Optional[int] = Field(None, description="Dénivelé cible")
    
    # Objectifs de la semaine
    focus: Optional[str] = Field(None, description="Focus principal (ex: 'VMA')")
    key_session_id: Optional[str] = Field(None, description="ID de la séance clé")
    
    notes: Optional[str] = Field(None, description="Notes pour la semaine")
    
    def add_session(self, session: TrainingSession):
        """Ajoute une séance à la semaine"""
        # Calculer la date de la séance
        session_date = self.start_date + timedelta(days=session.day_of_week - 1)
        session.scheduled_date = session_date
        session.week_number = self.week_number
        self.sessions.append(session)
    
    def get_total_volume(self) -> float:
        """Calcule le volume total planifié"""
        return sum(s.get_total_distance() for s in self.sessions)
    
    def get_total_duration(self) -> int:
        """Calcule la durée totale planifiée"""
        return sum(s.duration_minutes for s in self.sessions)
    
    def get_session_by_day(self, day: int) -> Optional[TrainingSession]:
        """Récupère la séance d'un jour donné (1=lundi)"""
        for session in self.sessions:
            if session.day_of_week == day:
                return session
        return None
    
    def get_completion_rate(self) -> float:
        """Taux de complétion de la semaine (0-1)"""
        if not self.sessions:
            return 0.0
        completed = sum(1 for s in self.sessions if s.is_completed())
        return completed / len(self.sessions)


class TrainingPlan(BaseModel):
    """Plan d'entraînement complet"""
    id: str = Field(..., description="ID unique du plan")
    name: str = Field(..., description="Nom du plan")
    description: str = Field(..., description="Description du plan")
    
    # Objectif
    goal_distance: str = Field(..., description="Distance cible (ex: 'Semi-marathon')")
    goal_time: str = Field(..., description="Temps cible (ex: '1:45:00')")
    target_pace_per_km: str = Field(..., description="Allure cible (ex: '4:58')")
    
    # Dates
    start_date: date = Field(..., description="Date de début du plan")
    end_date: date = Field(..., description="Date de fin (course)")
    duration_weeks: int = Field(..., ge=1, le=52)
    
    # Structure
    weeks: list[TrainingWeek] = Field(default_factory=list)
    
    # Configuration
    sessions_per_week: int = Field(default=4, ge=2, le=7)
    preferred_training_days: list[int] = Field(
        default=[2, 4, 6, 7],
        description="Jours préférés (1=lundi)"
    )
    
    # Athlète assigné
    athlete_id: str = Field(..., description="ID de l'athlète")
    
    # Métadonnées
    created_at: str = Field(default_factory=lambda: str(date.today()))
    is_active: bool = Field(default=True)
    
    def add_week(self, week: TrainingWeek):
        """Ajoute une semaine au plan"""
        self.weeks.append(week)
    
    def get_week(self, week_number: int) -> Optional[TrainingWeek]:
        """Récupère une semaine par son numéro"""
        for week in self.weeks:
            if week.week_number == week_number:
                return week
        return None
    
    def get_current_week(self) -> Optional[TrainingWeek]:
        """Récupère la semaine en cours"""
        today = date.today()
        for week in self.weeks:
            if week.start_date <= today <= week.end_date:
                return week
        return None
    
    def get_next_session(self) -> Optional[TrainingSession]:
        """Récupère la prochaine séance planifiée"""
        today = date.today()
        upcoming_sessions = []
        
        for week in self.weeks:
            for session in week.sessions:
                if session.scheduled_date and session.scheduled_date >= today:
                    if session.status.value in ["Planifiée", "Adaptée"]:
                        upcoming_sessions.append(session)
        
        if not upcoming_sessions:
            return None
        
        # Retourner la plus proche
        return min(upcoming_sessions, key=lambda s: s.scheduled_date)
    
    def get_total_volume(self) -> float:
        """Volume total du plan"""
        return sum(week.get_total_volume() for week in self.weeks)
    
    def get_completion_rate(self) -> float:
        """Taux de complétion global"""
        if not self.weeks:
            return 0.0
        total_sessions = sum(len(week.sessions) for week in self.weeks)
        if total_sessions == 0:
            return 0.0
        completed_sessions = sum(
            sum(1 for s in week.sessions if s.is_completed())
            for week in self.weeks
        )
        return completed_sessions / total_sessions
    
    def get_weeks_by_phase(self, phase: TrainingPhase) -> list[TrainingWeek]:
        """Récupère toutes les semaines d'une phase"""
        return [week for week in self.weeks if week.phase == phase]
    
    def get_stats(self) -> dict:
        """Statistiques du plan"""
        total_sessions = sum(len(week.sessions) for week in self.weeks)
        completed = sum(
            sum(1 for s in week.sessions if s.is_completed())
            for week in self.weeks
        )
        
        return {
            'total_weeks': len(self.weeks),
            'total_sessions': total_sessions,
            'completed_sessions': completed,
            'completion_rate': self.get_completion_rate(),
            'total_volume_km': self.get_total_volume(),
            'current_week': self.get_current_week().week_number if self.get_current_week() else None,
            'weeks_remaining': (self.end_date - date.today()).days // 7 if date.today() <= self.end_date else 0
        }
    
    def get_statistics(self) -> dict:
        """Statistiques détaillées du plan par phase et type de séance"""
        # Comptage par phase
        phases = {}
        for week in self.weeks:
            phase_name = week.phase.value
            phases[phase_name] = phases.get(phase_name, 0) + 1
        
        # Comptage par type de séance
        session_types = {}
        for week in self.weeks:
            for session in week.sessions:
                session_type = session.session_type.value
                session_types[session_type] = session_types.get(session_type, 0) + 1
        
        return {
            'phases': phases,
            'session_types': session_types,
            'total_weeks': len(self.weeks),
            'total_sessions': sum(len(week.sessions) for week in self.weeks),
            'total_volume_km': round(self.get_total_volume(), 1)
        }
    
    def generate_calendar_export(self) -> list[dict]:
        """Génère une liste d'événements pour export Google Calendar"""
        events = []
        for week in self.weeks:
            for session in week.sessions:
                if session.scheduled_date and session.scheduled_time:
                    # Parse time
                    hour, minute = map(int, session.scheduled_time.split(':'))
                    start = session.scheduled_date.isoformat() + f"T{hour:02d}:{minute:02d}:00"
                    
                    # End time
                    end_hour = hour + (session.duration_minutes // 60)
                    end_minute = minute + (session.duration_minutes % 60)
                    if end_minute >= 60:
                        end_hour += 1
                        end_minute -= 60
                    end = session.scheduled_date.isoformat() + f"T{end_hour:02d}:{end_minute:02d}:00"
                    
                    events.append({
                        'summary': session.title,
                        'description': session.description,
                        'start': start,
                        'end': end,
                        'session_id': session.id
                    })
        return events


def create_week_dates(start_date: date, week_number: int) -> tuple[date, date]:
    """Helper: crée les dates de début et fin pour une semaine"""
    week_start = start_date + timedelta(weeks=week_number - 1)
    # Assurer que c'est un lundi
    while week_start.weekday() != 0:  # 0 = lundi
        week_start -= timedelta(days=1)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end
