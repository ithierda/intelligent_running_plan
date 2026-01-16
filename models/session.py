"""
Modèle de données pour une séance d'entraînement
"""
from pydantic import BaseModel, Field, field_validator, computed_field
from enum import Enum
from datetime import datetime, date
from typing import Optional


class SessionType(str, Enum):
    """Types de séances d'entraînement"""
    ENDURANCE = "Endurance fondamentale"
    TEMPO = "Tempo/Allure spécifique"
    THRESHOLD = "Seuil"
    INTERVALS = "Fractionné VMA"
    LONG_RUN = "Sortie longue"
    RECOVERY = "Récupération active"
    RACE = "Course/Test"
    REST = "Repos complet"
    FARTLEK = "Fartlek"


class SessionIntensity(str, Enum):
    """Niveau d'intensité"""
    VERY_EASY = "Très facile"
    EASY = "Facile"
    MODERATE = "Modéré"
    HARD = "Difficile"
    VERY_HARD = "Très difficile"


class SessionStatus(str, Enum):
    """Statut de la séance"""
    PLANNED = "Planifiée"
    ADAPTED = "Adaptée"
    COMPLETED = "Effectuée"
    SKIPPED = "Sautée"
    POSTPONED = "Reportée"


class PaceZone(BaseModel):
    """Zone d'allure pour une portion de séance"""
    description: str = Field(..., description="Description de la portion (ex: 'Échauffement')")
    duration_minutes: Optional[int] = Field(None, description="Durée en minutes")
    distance_km: Optional[float] = Field(None, description="Distance en km")
    pace_min_per_km: str = Field(..., description="Allure en min/km (ex: '5:00')")
    pace_max_per_km: Optional[str] = Field(None, description="Allure max si zone")
    hr_zone: Optional[str] = Field(None, description="Zone FC (ex: '80-85% FCmax')")
    repetitions: int = Field(1, description="Nombre de répétitions")
    recovery_minutes: Optional[float] = Field(None, description="Récupération entre reps (min)")

    @field_validator('pace_min_per_km', 'pace_max_per_km')
    @classmethod
    def validate_pace_format(cls, v):
        """Valide le format d'allure MM:SS"""
        if v is None:
            return v
        try:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError
            int(parts[0])  # minutes
            int(parts[1])  # secondes
            return v
        except:
            raise ValueError(f"Format d'allure invalide: {v}. Utilisez MM:SS (ex: '5:30')")


class TrainingSession(BaseModel):
    """Modèle complet d'une séance d'entraînement"""
    id: str = Field(..., description="ID unique de la séance")
    week_number: int = Field(..., ge=1, le=52, description="Numéro de semaine du plan")
    day_of_week: int = Field(..., ge=1, le=7, description="Jour de la semaine (1=lundi)")
    session_number: int = Field(..., description="Numéro de la séance dans la semaine")
    
    # Type et caractéristiques
    session_type: SessionType
    intensity: SessionIntensity
    title: str = Field(..., description="Titre court (ex: 'Seuil 3x10min')")
    description: str = Field(..., description="Description complète de la séance")
    
    # Durée et distance
    duration_minutes: int = Field(..., gt=0, description="Durée totale estimée")
    distance_km: Optional[float] = Field(None, description="Distance totale estimée")
    
    # Structure détaillée
    structure: list[PaceZone] = Field(default_factory=list, description="Détail des portions")
    
    # Scheduling
    scheduled_date: Optional[date] = Field(None, description="Date planifiée")
    scheduled_time: Optional[str] = Field(None, description="Heure planifiée (HH:MM)")
    
    # Statut et adaptation
    status: SessionStatus = Field(default=SessionStatus.PLANNED)
    adaptation_reason: Optional[str] = Field(None, description="Raison de l'adaptation")
    original_session_id: Optional[str] = Field(None, description="ID séance originale si adaptée")
    
    # Importance et flexibilité
    is_key_session: bool = Field(False, description="Séance clé du plan (moins flexible)")
    can_be_postponed: bool = Field(True, description="Peut être reportée")
    can_be_replaced: bool = Field(True, description="Peut être remplacée")
    
    # Données post-séance (si effectuée)
    completed_at: Optional[datetime] = Field(None, description="Timestamp de complétion")
    actual_duration_minutes: Optional[int] = Field(None)
    actual_distance_km: Optional[float] = Field(None)
    average_pace: Optional[str] = Field(None, description="Allure moyenne (MM:SS)")
    average_hr: Optional[int] = Field(None, description="FC moyenne")
    max_hr: Optional[int] = Field(None, description="FC max")
    rpe: Optional[int] = Field(None, ge=1, le=10, description="RPE (1-10)")
    feeling: Optional[str] = Field(None, description="Ressenti libre")
    
    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @computed_field
    @property
    def load_score(self) -> int:
        """
        Calcule le score de charge de la séance (0-100)
        Basé sur la durée et l'intensité
        """
        # Base : durée (30min = 30 points, max 60)
        duration_score = min(self.duration_minutes * 0.5, 60)
        
        # Multiplicateur d'intensité
        intensity_multipliers = {
            SessionIntensity.VERY_EASY: 0.5,
            SessionIntensity.EASY: 0.7,
            SessionIntensity.MODERATE: 1.0,
            SessionIntensity.HARD: 1.3,
            SessionIntensity.VERY_HARD: 1.5
        }
        
        multiplier = intensity_multipliers.get(self.intensity, 1.0)
        score = duration_score * multiplier
        
        # Bonus séance clé
        if self.is_key_session:
            score *= 1.1
            
        return int(min(score, 100))

    def get_total_distance(self) -> float:
        """Calcule la distance totale à partir de la structure"""
        if self.distance_km:
            return self.distance_km
        total = sum(
            (zone.distance_km or 0) * zone.repetitions 
            for zone in self.structure
        )
        return round(total, 2)

    def get_workout_summary(self) -> str:
        """Retourne un résumé textuel de la séance"""
        parts = []
        for zone in self.structure:
            rep_str = f"{zone.repetitions}x " if zone.repetitions > 1 else ""
            if zone.distance_km:
                parts.append(f"{rep_str}{zone.distance_km}km @ {zone.pace_min_per_km}/km")
            elif zone.duration_minutes:
                parts.append(f"{rep_str}{zone.duration_minutes}min @ {zone.pace_min_per_km}/km")
            if zone.recovery_minutes and zone.repetitions > 1:
                parts.append(f"(récup {zone.recovery_minutes}min)")
        return " + ".join(parts)

    def is_completed(self) -> bool:
        """Vérifie si la séance est complétée"""
        return self.status == SessionStatus.COMPLETED

    def mark_as_completed(self, actual_data: dict):
        """Marque la séance comme effectuée avec les données réelles"""
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now()
        self.actual_duration_minutes = actual_data.get('duration_minutes')
        self.actual_distance_km = actual_data.get('distance_km')
        self.average_pace = actual_data.get('average_pace')
        self.average_hr = actual_data.get('average_hr')
        self.max_hr = actual_data.get('max_hr')
        self.rpe = actual_data.get('rpe')
        self.feeling = actual_data.get('feeling')
        self.updated_at = datetime.now()

    def adapt_session(self, new_type: SessionType = None, 
                     reduction_factor: float = 1.0, 
                     reason: str = ""):
        """
        Adapte la séance (allégement ou changement)
        reduction_factor: 0.7 = réduction de 30%
        """
        self.status = SessionStatus.ADAPTED
        self.adaptation_reason = reason
        self.updated_at = datetime.now()
        
        if new_type:
            self.original_session_id = self.id
            self.session_type = new_type
        
        if reduction_factor < 1.0:
            self.duration_minutes = int(self.duration_minutes * reduction_factor)
            if self.distance_km:
                self.distance_km = round(self.distance_km * reduction_factor, 2)
            # Adapter aussi la structure
            for zone in self.structure:
                if zone.duration_minutes:
                    zone.duration_minutes = int(zone.duration_minutes * reduction_factor)
                if zone.distance_km:
                    zone.distance_km = round(zone.distance_km * reduction_factor, 2)


# Exemples de séances pré-définies
EXAMPLE_SESSIONS = {
    "endurance_60": TrainingSession(
        id="E60",
        week_number=1,
        day_of_week=1,
        session_number=1,
        session_type=SessionType.ENDURANCE,
        intensity=SessionIntensity.EASY,
        title="Endurance 60min",
        description="Course à allure conversationnelle, 75-80% FCmax",
        duration_minutes=60,
        distance_km=10.0,
        structure=[
            PaceZone(
                description="Endurance fondamentale",
                duration_minutes=60,
                pace_min_per_km="6:00",
                pace_max_per_km="6:15",
                hr_zone="75-80% FCmax"
            )
        ]
    ),
    "threshold_3x10": TrainingSession(
        id="T3x10",
        week_number=5,
        day_of_week=3,
        session_number=2,
        session_type=SessionType.THRESHOLD,
        intensity=SessionIntensity.HARD,
        title="Seuil 3x10min",
        description="3 blocs de 10min à allure semi, récup 2min trot",
        duration_minutes=60,
        distance_km=12.0,
        is_key_session=True,
        structure=[
            PaceZone(description="Échauffement", duration_minutes=15, 
                    pace_min_per_km="6:00", hr_zone="70-75% FCmax"),
            PaceZone(description="Bloc seuil", duration_minutes=10, 
                    pace_min_per_km="4:55", pace_max_per_km="5:00",
                    hr_zone="87-92% FCmax", repetitions=3, recovery_minutes=2),
            PaceZone(description="Retour au calme", duration_minutes=10, 
                    pace_min_per_km="6:15")
        ]
    ),
    "vma_10x400": TrainingSession(
        id="VMA10x400",
        week_number=6,
        day_of_week=2,
        session_number=1,
        session_type=SessionType.INTERVALS,
        intensity=SessionIntensity.VERY_HARD,
        title="VMA 10x400m",
        description="10 répétitions de 400m à VMA, récup 1min30 trot",
        duration_minutes=55,
        distance_km=9.0,
        is_key_session=True,
        structure=[
            PaceZone(description="Échauffement", duration_minutes=15, 
                    pace_min_per_km="6:00"),
            PaceZone(description="400m VMA", distance_km=0.4, 
                    pace_min_per_km="3:30", hr_zone="95-100% FCmax",
                    repetitions=10, recovery_minutes=1.5),
            PaceZone(description="Retour au calme", duration_minutes=10, 
                    pace_min_per_km="6:30")
        ]
    )
}
