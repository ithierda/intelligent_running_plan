"""
Modèle de données pour le profil athlète
"""
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional
from enum import Enum


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Other"


class ExperienceLevel(str, Enum):
    """Niveau d'expérience en course à pied"""
    BEGINNER = "Débutant"  # < 6 mois
    INTERMEDIATE = "Intermédiaire"  # 6 mois - 2 ans
    ADVANCED = "Avancé"  # 2-5 ans
    EXPERT = "Expert"  # > 5 ans


class RaceGoal(BaseModel):
    """Objectif de course"""
    distance: str = Field(..., description="Distance (ex: 'Semi-marathon', '10km')")
    target_time: str = Field(..., description="Temps cible (ex: '1:45:00')")
    race_date: Optional[date] = Field(None, description="Date de la course")
    priority: int = Field(1, ge=1, le=3, description="Priorité (1=haute, 3=basse)")


class TrainingPreferences(BaseModel):
    """Préférences d'entraînement"""
    preferred_days: list[int] = Field(
        default=[2, 4, 6],
        description="Jours préférés (1=lundi, 7=dimanche)"
    )
    preferred_time: str = Field(
        default="18:00",
        description="Heure préférée (HH:MM)"
    )
    sessions_per_week: int = Field(
        default=4,
        ge=2,
        le=7,
        description="Nombre de séances par semaine"
    )
    preferred_surfaces: list[str] = Field(
        default=["Route", "Piste"],
        description="Surfaces préférées"
    )
    available_equipment: list[str] = Field(
        default=["Chronomètre", "Cardio"],
        description="Équipement disponible"
    )
    max_session_duration: int = Field(
        default=120,
        description="Durée max d'une séance (minutes)"
    )


class PhysiologicalData(BaseModel):
    """Données physiologiques de l'athlète"""
    age: int = Field(..., ge=10, le=100)
    gender: Gender
    weight_kg: float = Field(..., gt=30, lt=200)
    height_cm: int = Field(..., gt=100, lt=250)
    
    # Métriques de performance
    vma_kmh: Optional[float] = Field(
        None, 
        gt=8, 
        lt=25,
        description="VMA en km/h (test ou estimé)"
    )
    vo2max: Optional[float] = Field(
        None,
        gt=20,
        lt=90,
        description="VO2max ml/kg/min (Garmin ou test)"
    )
    max_hr: Optional[int] = Field(
        None,
        gt=100,
        lt=220,
        description="Fréquence cardiaque maximale"
    )
    resting_hr: Optional[int] = Field(
        None,
        gt=30,
        lt=100,
        description="FC repos moyenne"
    )
    lactate_threshold_hr: Optional[int] = Field(
        None,
        description="FC au seuil lactique"
    )
    
    # Calculs automatiques
    def calculate_max_hr_estimate(self) -> int:
        """Estime FCmax si non fournie (formule 220 - âge)"""
        if self.max_hr:
            return self.max_hr
        return 220 - self.age
    
    def calculate_vma_from_vo2max(self) -> float:
        """Estime VMA à partir du VO2max"""
        if self.vma_kmh:
            return self.vma_kmh
        if self.vo2max:
            # Formule approximative: VMA (km/h) ≈ VO2max / 3.5
            return round(self.vo2max / 3.5, 1)
        return 15.0  # Valeur par défaut raisonnable
    
    def get_training_zones(self) -> dict:
        """Calcule les zones d'entraînement"""
        max_hr = self.calculate_max_hr_estimate()
        return {
            "Z1_recovery": (max_hr * 0.60, max_hr * 0.70),
            "Z2_endurance": (max_hr * 0.70, max_hr * 0.80),
            "Z3_tempo": (max_hr * 0.80, max_hr * 0.87),
            "Z4_threshold": (max_hr * 0.87, max_hr * 0.92),
            "Z5_vma": (max_hr * 0.92, max_hr * 1.00),
        }


class PerformanceHistory(BaseModel):
    """Historique de performances"""
    date: date
    distance: str  # "5km", "10km", "Semi", "Marathon"
    time: str  # "HH:MM:SS"
    pace_per_km: str  # "MM:SS"
    race_or_training: str = "Race"  # "Race" ou "Training"


class Athlete(BaseModel):
    """Profil complet de l'athlète"""
    # Identité
    id: str = Field(..., description="ID unique")
    name: str = Field(..., description="Nom complet")
    email: str = Field(..., description="Email")
    
    # Données physio
    physio: PhysiologicalData
    
    # Expérience
    experience_level: ExperienceLevel
    running_since: Optional[date] = Field(
        None, 
        description="Date de début de la pratique"
    )
    
    # Objectifs
    primary_goal: RaceGoal
    secondary_goals: list[RaceGoal] = Field(default_factory=list)
    
    # Préférences
    preferences: TrainingPreferences
    
    # Historique
    performance_history: list[PerformanceHistory] = Field(default_factory=list)
    
    # Connexions API
    garmin_connected: bool = False
    google_calendar_connected: bool = False
    apple_health_connected: bool = False
    
    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_best_performance(self, distance: str) -> Optional[PerformanceHistory]:
        """Retourne la meilleure perf pour une distance donnée"""
        perfs = [p for p in self.performance_history if p.distance == distance]
        if not perfs:
            return None
        return min(perfs, key=lambda p: p.time)
    
    def get_current_fitness_level(self) -> str:
        """Estime le niveau actuel basé sur VO2max ou VMA"""
        vo2 = self.physio.vo2max
        if not vo2:
            return "Non évalué"
        
        # Barèmes approximatifs pour hommes (à ajuster selon genre/âge)
        if vo2 < 35:
            return "Faible"
        elif vo2 < 45:
            return "Moyen"
        elif vo2 < 55:
            return "Bon"
        elif vo2 < 65:
            return "Très bon"
        else:
            return "Excellent"
    
    def calculate_race_pace(self, distance: str) -> str:
        """
        Calcule l'allure de course recommandée pour une distance
        basée sur la VMA
        """
        vma = self.physio.calculate_vma_from_vo2max()
        
        # Pourcentages de VMA par distance (estimations)
        vma_percentages = {
            "5km": 0.95,
            "10km": 0.90,
            "Semi-marathon": 0.85,
            "Marathon": 0.80
        }
        
        pct = vma_percentages.get(distance, 0.85)
        race_speed_kmh = vma * pct
        
        # Convertir en min/km
        pace_min_per_km = 60 / race_speed_kmh
        minutes = int(pace_min_per_km)
        seconds = int((pace_min_per_km - minutes) * 60)
        
        return f"{minutes}:{seconds:02d}"
    
    def weeks_until_goal(self) -> Optional[int]:
        """Retourne le nombre de semaines jusqu'à l'objectif principal"""
        if not self.primary_goal.race_date:
            return None
        delta = self.primary_goal.race_date - date.today()
        return delta.days // 7


# Exemple d'athlète
EXAMPLE_ATHLETE = Athlete(
    id="athlete_001",
    name="Ithier DARAMON",
    email="ithier.da@gmail.com",
    physio=PhysiologicalData(
        age=25,
        gender=Gender.MALE,
        weight_kg=70,
        height_cm=178,
        vma_kmh=17.0,
        vo2max=55,
        max_hr=195,
        resting_hr=48
    ),
    experience_level=ExperienceLevel.ADVANCED,
    primary_goal=RaceGoal(
        distance="Semi-marathon",
        target_time="1:45:00",
        race_date=date(2026, 4, 12),  # Exemple
        priority=1
    ),
    preferences=TrainingPreferences(
        preferred_days=[2, 4, 6, 7],  # Mar, Jeu, Sam, Dim
        preferred_time="18:00",
        sessions_per_week=4,
        preferred_surfaces=["Route", "Piste", "Trail"],
        available_equipment=["Garmin", "Cardio", "Accès piste"]
    ),
    performance_history=[
        PerformanceHistory(
            date=date(2025, 10, 15),
            distance="10km",
            time="00:42:30",
            pace_per_km="4:15"
        ),
        PerformanceHistory(
            date=date(2025, 5, 20),
            distance="Semi-marathon",
            time="1:52:00",
            pace_per_km="5:18"
        )
    ]
)
