"""
Modèle de profil athlète
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List
from enum import Enum


class Gender(Enum):
    """Genre de l'athlète"""
    MALE = "Homme"
    FEMALE = "Femme"


class TrainingLevel(Enum):
    """Niveau d'entraînement"""
    BEGINNER = "Débutant"
    INTERMEDIATE = "Intermédiaire"
    ADVANCED = "Avancé"
    ELITE = "Elite"


class PreferredTerrain(Enum):
    """Terrain préféré"""
    ROAD = "Route"
    TRAIL = "Trail"
    TRACK = "Piste"
    MIXED = "Mixte"


class PreferredTime(Enum):
    """Moment préféré de la journée"""
    MORNING = "Matin (6h-10h)"
    MIDDAY = "Midi (11h-14h)"
    AFTERNOON = "Après-midi (15h-18h)"
    EVENING = "Soir (19h-22h)"


@dataclass
class AthleteProfile:
    """Profil complet d'un athlète"""
    
    # Informations personnelles
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    
    # Données physiologiques
    weight_kg: float  # Poids en kg
    height_cm: Optional[int] = None  # Taille en cm
    
    # Données cardiaques
    max_heart_rate: Optional[int] = None  # FC max (si None, calcul 220 - âge)
    resting_heart_rate: Optional[int] = None  # FC repos habituelle
    
    # Capacités
    vma_kmh: Optional[float] = None  # VMA en km/h
    threshold_pace_min_per_km: Optional[str] = None  # Allure seuil (ex: "4:30")
    
    # Niveau et expérience
    training_level: TrainingLevel = TrainingLevel.INTERMEDIATE
    running_experience_years: Optional[int] = None
    
    # Préférences d'entraînement
    preferred_training_times: List[PreferredTime] = field(default_factory=list)
    preferred_terrain: PreferredTerrain = PreferredTerrain.ROAD
    
    # Historique de blessures
    injury_history: List[str] = field(default_factory=list)
    current_injuries: List[str] = field(default_factory=list)
    
    # Objectifs
    main_goal: Optional[str] = None  # Objectif principal (ex: "Semi-marathon sub 1:45")
    secondary_goals: List[str] = field(default_factory=list)
    
    # Configuration externe
    garmin_email: Optional[str] = None
    garmin_connected: bool = False
    google_calendar_connected: bool = False
    
    # Métadonnées
    created_at: date = field(default_factory=date.today)
    updated_at: date = field(default_factory=date.today)
    
    def get_age(self) -> int:
        """Calcule l'âge actuel"""
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    def get_max_heart_rate(self) -> int:
        """
        Retourne la FC max (mesurée ou calculée)
        Formule par défaut : 220 - âge
        """
        if self.max_heart_rate:
            return self.max_heart_rate
        return 220 - self.get_age()
    
    def get_heart_rate_zones(self) -> dict:
        """
        Calcule les zones de fréquence cardiaque
        
        Returns:
            dict avec les zones Z1-Z5
        """
        fc_max = self.get_max_heart_rate()
        
        return {
            "Z1_recovery": (int(fc_max * 0.50), int(fc_max * 0.60)),
            "Z2_endurance": (int(fc_max * 0.60), int(fc_max * 0.70)),
            "Z3_tempo": (int(fc_max * 0.70), int(fc_max * 0.80)),
            "Z4_threshold": (int(fc_max * 0.80), int(fc_max * 0.90)),
            "Z5_vo2max": (int(fc_max * 0.90), int(fc_max * 1.00))
        }
    
    def get_bmi(self) -> Optional[float]:
        """Calcule l'IMC si la taille est renseignée"""
        if self.height_cm:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None
    
    def estimate_vo2max(self) -> Optional[float]:
        """
        Estime la VO2max basée sur la VMA
        Formule approximative: VO2max ≈ 3.5 × VMA
        """
        if self.vma_kmh:
            return round(3.5 * self.vma_kmh, 1)
        return None
    
    def to_dict(self) -> dict:
        """Convertit le profil en dictionnaire pour sauvegarde"""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'birth_date': self.birth_date.isoformat(),
            'gender': self.gender.value,
            'weight_kg': self.weight_kg,
            'height_cm': self.height_cm,
            'max_heart_rate': self.max_heart_rate,
            'resting_heart_rate': self.resting_heart_rate,
            'vma_kmh': self.vma_kmh,
            'threshold_pace_min_per_km': self.threshold_pace_min_per_km,
            'training_level': self.training_level.value,
            'running_experience_years': self.running_experience_years,
            'preferred_training_times': [t.value for t in self.preferred_training_times],
            'preferred_terrain': self.preferred_terrain.value,
            'injury_history': self.injury_history,
            'current_injuries': self.current_injuries,
            'main_goal': self.main_goal,
            'secondary_goals': self.secondary_goals,
            'garmin_email': self.garmin_email,
            'garmin_connected': self.garmin_connected,
            'google_calendar_connected': self.google_calendar_connected,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AthleteProfile':
        """Reconstruit un profil depuis un dictionnaire"""
        from datetime import date as dt_date
        
        return cls(
            first_name=data['first_name'],
            last_name=data['last_name'],
            birth_date=dt_date.fromisoformat(data['birth_date']),
            gender=Gender(data['gender']),
            weight_kg=data['weight_kg'],
            height_cm=data.get('height_cm'),
            max_heart_rate=data.get('max_heart_rate'),
            resting_heart_rate=data.get('resting_heart_rate'),
            vma_kmh=data.get('vma_kmh'),
            threshold_pace_min_per_km=data.get('threshold_pace_min_per_km'),
            training_level=TrainingLevel(data.get('training_level', TrainingLevel.INTERMEDIATE.value)),
            running_experience_years=data.get('running_experience_years'),
            preferred_training_times=[PreferredTime(t) for t in data.get('preferred_training_times', [])],
            preferred_terrain=PreferredTerrain(data.get('preferred_terrain', PreferredTerrain.ROAD.value)),
            injury_history=data.get('injury_history', []),
            current_injuries=data.get('current_injuries', []),
            main_goal=data.get('main_goal'),
            secondary_goals=data.get('secondary_goals', []),
            garmin_email=data.get('garmin_email'),
            garmin_connected=data.get('garmin_connected', False),
            google_calendar_connected=data.get('google_calendar_connected', False),
            created_at=dt_date.fromisoformat(data.get('created_at', dt_date.today().isoformat())),
            updated_at=dt_date.fromisoformat(data.get('updated_at', dt_date.today().isoformat()))
        )
