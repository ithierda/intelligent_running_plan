"""
Modèle de données pour les métriques quotidiennes (sommeil, récupération, charge)
"""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from enum import Enum


class SleepQuality(str, Enum):
    """Qualité du sommeil"""
    POOR = "Mauvaise"
    FAIR = "Moyenne"
    GOOD = "Bonne"
    EXCELLENT = "Excellente"


class StressLevel(str, Enum):
    """Niveau de stress"""
    LOW = "Faible"
    MODERATE = "Modéré"
    HIGH = "Élevé"
    VERY_HIGH = "Très élevé"


class ReadinessLevel(str, Enum):
    """Niveau de préparation globale"""
    POOR = "Mauvais"
    COMPROMISED = "Compromis"
    OK = "Correct"
    GOOD = "Bon"
    OPTIMAL = "Optimal"


class SleepData(BaseModel):
    """Données de sommeil (Garmin, Apple Health)"""
    date: date
    total_sleep_hours: float = Field(..., ge=0, le=24, description="Durée totale sommeil")
    deep_sleep_hours: Optional[float] = Field(None, description="Sommeil profond")
    rem_sleep_hours: Optional[float] = Field(None, description="Sommeil paradoxal")
    light_sleep_hours: Optional[float] = Field(None, description="Sommeil léger")
    awake_hours: Optional[float] = Field(None, description="Temps éveillé")
    
    sleep_quality: SleepQuality
    sleep_score: int = Field(..., ge=0, le=150, description="Score de qualité (0-100, Garmin peut dépasser)")
    
    bedtime: Optional[str] = Field(None, description="Heure coucher (HH:MM)")
    wake_time: Optional[str] = Field(None, description="Heure réveil (HH:MM)")
    
    source: str = Field(default="Garmin", description="Source des données")
    
    def get_sleep_efficiency(self) -> float:
        """Calcule l'efficacité du sommeil (temps dormi / temps au lit)"""
        if not self.awake_hours:
            return 1.0
        total_bed_time = self.total_sleep_hours + self.awake_hours
        if total_bed_time == 0:
            return 0.0
        return round(self.total_sleep_hours / total_bed_time, 2)
    
    def is_sleep_sufficient(self, target_hours: float = 7.5) -> bool:
        """Vérifie si le sommeil est suffisant"""
        return self.total_sleep_hours >= target_hours
    
    def get_normalized_score(self) -> float:
        """Retourne un score normalisé 0-1 (plafonne à 1.0 si > 100)"""
        return min(self.sleep_score / 100.0, 1.0)


class HeartRateVariability(BaseModel):
    """Données de variabilité de la fréquence cardiaque (HRV)"""
    date: date
    hrv_ms: float = Field(..., gt=0, description="HRV en millisecondes (RMSSD)")
    source: str = Field(default="Garmin")
    
    # Contexte de la mesure
    measured_at: Optional[str] = Field(None, description="Heure de mesure")
    measured_during_sleep: bool = Field(True)
    
    def get_normalized_score(self, baseline_hrv: float = 50.0) -> float:
        """
        Score normalisé par rapport à une baseline personnelle
        >baseline = bon (max 1.0), <baseline = fatigue (min 0.0)
        """
        if baseline_hrv == 0:
            return 0.5
        ratio = self.hrv_ms / baseline_hrv
        # Score entre 0 et 1, centré sur 1.0 quand ratio=1
        return min(1.0, max(0.0, ratio))


class RestingHeartRate(BaseModel):
    """Fréquence cardiaque au repos"""
    date: date
    rhr_bpm: int = Field(..., gt=30, lt=120, description="FC repos en BPM")
    source: str = Field(default="Garmin")
    
    def get_normalized_score(self, baseline_rhr: int = 50) -> float:
        """
        Score normalisé: FC plus basse que baseline = meilleure récup
        """
        if baseline_rhr == 0:
            return 0.5
        # Inverser car FC basse = bon
        ratio = baseline_rhr / self.rhr_bpm
        return min(1.0, max(0.0, ratio))


class TrainingLoad(BaseModel):
    """Charge d'entraînement"""
    date: date
    
    # Charge aiguë et chronique
    acute_load: float = Field(
        default=0.0,
        description="Charge des 7 derniers jours"
    )
    chronic_load: float = Field(
        default=0.0,
        description="Charge des 28 derniers jours (moyenne)"
    )
    
    # ACWR - Acute:Chronic Workload Ratio
    acwr: Optional[float] = Field(None, description="Ratio charge aiguë/chronique")
    
    # Données Garmin spécifiques
    training_stress_score: Optional[int] = Field(None, description="TSS Garmin")
    body_battery: Optional[int] = Field(None, ge=0, le=100, description="Body Battery")
    
    source: str = Field(default="Calculated")
    
    def calculate_acwr(self) -> float:
        """Calcule le ratio ACWR"""
        if self.chronic_load == 0:
            return 1.0
        ratio = self.acute_load / self.chronic_load
        self.acwr = round(ratio, 2)
        return self.acwr
    
    def get_fatigue_status(self) -> str:
        """Interprète l'ACWR"""
        if not self.acwr:
            self.calculate_acwr()
        
        if self.acwr < 0.8:
            return "Sous-entraîné"
        elif 0.8 <= self.acwr <= 1.3:
            return "Zone optimale"
        elif 1.3 < self.acwr <= 1.5:
            return "Fatigue légère"
        else:
            return "Surcharge importante"
    
    def get_normalized_score(self) -> float:
        """Score basé sur ACWR (optimal = 1.0, extrêmes = 0.0)"""
        if not self.acwr:
            self.calculate_acwr()
        
        # Score optimal entre 0.8 et 1.3
        if 0.8 <= self.acwr <= 1.3:
            return 1.0
        elif self.acwr < 0.8:
            # Sous-entraîné: score décroît quand on s'éloigne de 0.8
            return max(0.0, self.acwr / 0.8)
        else:
            # Sur-entraîné: score décroît après 1.3
            return max(0.0, 1.0 - (self.acwr - 1.3) / 0.7)


class SubjectiveMetrics(BaseModel):
    """Métriques subjectives déclarées par l'athlète"""
    date: date
    
    # RPE = Rating of Perceived Exertion
    rpe: Optional[int] = Field(None, ge=1, le=10, description="RPE 1-10")
    
    # Ressenti global
    motivation: Optional[int] = Field(None, ge=1, le=5, description="Motivation 1-5")
    energy: Optional[int] = Field(None, ge=1, le=5, description="Énergie 1-5")
    mood: Optional[int] = Field(None, ge=1, le=5, description="Humeur 1-5")
    
    # Douleurs
    muscle_soreness: Optional[int] = Field(None, ge=1, le=5, description="Courbatures 1-5")
    injury_risk: Optional[int] = Field(None, ge=1, le=5, description="Risque blessure 1-5")
    
    # Note générale
    overall_feeling: Optional[str] = Field(None, description="Ressenti libre")
    
    def get_normalized_score(self) -> float:
        """Calcule un score global 0-1"""
        scores = []
        
        if self.motivation:
            scores.append(self.motivation / 5)
        if self.energy:
            scores.append(self.energy / 5)
        if self.mood:
            scores.append(self.mood / 5)
        if self.muscle_soreness:
            # Inverser car soreness élevée = mauvais
            scores.append(1 - (self.muscle_soreness - 1) / 4)
        
        if not scores:
            return 0.5  # Neutre si pas de données
        
        return sum(scores) / len(scores)


class DailyMetrics(BaseModel):
    """Compilation de toutes les métriques d'un jour"""
    date: date
    
    # Données objectives
    sleep: Optional[SleepData] = None
    hrv: Optional[HeartRateVariability] = None
    rhr: Optional[RestingHeartRate] = None
    training_load: Optional[TrainingLoad] = None
    
    # Données subjectives
    subjective: Optional[SubjectiveMetrics] = None
    
    # Contraintes du jour
    calendar_busy_hours: int = Field(default=0, description="Heures occupées")
    available_time_slots: list[str] = Field(
        default_factory=list,
        description="Créneaux libres (HH:MM-HH:MM)"
    )
    
    # Contexte externe
    weather_condition: Optional[str] = Field(None, description="Météo")
    temperature_celsius: Optional[float] = Field(None)
    
    # Score de récupération global
    recovery_score: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Score global de récupération 0-100"
    )
    
    readiness_level: Optional[ReadinessLevel] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    
    def calculate_recovery_score(
        self,
        weights: dict = None,
        baseline_hrv: float = 50.0,
        baseline_rhr: int = 50
    ) -> float:
        """
        Calcule le score de récupération global (0-100)
        
        Formule par défaut:
        - 35% sommeil
        - 25% HRV
        - 20% charge d'entraînement
        - 10% FC repos
        - 10% ressenti subjectif
        """
        if weights is None:
            weights = {
                'sleep': 0.35,
                'hrv': 0.25,
                'load': 0.20,
                'rhr': 0.10,
                'subjective': 0.10
            }
        
        components = {}
        
        # Sommeil
        if self.sleep:
            components['sleep'] = self.sleep.get_normalized_score()
        
        # HRV
        if self.hrv:
            components['hrv'] = self.hrv.get_normalized_score(baseline_hrv)
        
        # Charge
        if self.training_load:
            components['load'] = self.training_load.get_normalized_score()
        
        # FC repos
        if self.rhr:
            components['rhr'] = self.rhr.get_normalized_score(baseline_rhr)
        
        # Subjectif
        if self.subjective:
            components['subjective'] = self.subjective.get_normalized_score()
        
        # Calculer le score pondéré
        total_weight = sum(weights[k] for k in components.keys())
        if total_weight == 0:
            self.recovery_score = 50.0  # Score neutre si pas de données
        else:
            score = sum(
                components[k] * weights[k] 
                for k in components.keys()
            )
            # Normaliser par le poids total réel
            self.recovery_score = round((score / total_weight) * 100, 1)
        
        # Déterminer le niveau de préparation
        if self.recovery_score >= 85:
            self.readiness_level = ReadinessLevel.OPTIMAL
        elif self.recovery_score >= 70:
            self.readiness_level = ReadinessLevel.GOOD
        elif self.recovery_score >= 55:
            self.readiness_level = ReadinessLevel.OK
        elif self.recovery_score >= 40:
            self.readiness_level = ReadinessLevel.COMPROMISED
        else:
            self.readiness_level = ReadinessLevel.POOR
        
        return self.recovery_score
    
    def has_available_time(self, required_minutes: int) -> bool:
        """Vérifie s'il y a assez de temps disponible"""
        # Simplification: assume 24h - calendar_busy_hours
        available_hours = 24 - self.calendar_busy_hours - 8  # 8h sommeil
        return (available_hours * 60) >= required_minutes
    
    def get_recommendation_factors(self) -> dict:
        """Retourne les facteurs pour la recommandation"""
        return {
            'recovery_score': self.recovery_score or 50.0,
            'readiness': self.readiness_level.value if self.readiness_level else "OK",
            'sleep_hours': self.sleep.total_sleep_hours if self.sleep else None,
            'acwr': self.training_load.acwr if self.training_load else None,
            'available_slots': len(self.available_time_slots),
            'weather': self.weather_condition
        }


# Exemple de métriques quotidiennes
EXAMPLE_DAILY_METRICS = DailyMetrics(
    date=date.today(),
    sleep=SleepData(
        date=date.today(),
        total_sleep_hours=7.5,
        deep_sleep_hours=1.8,
        rem_sleep_hours=2.0,
        light_sleep_hours=3.5,
        awake_hours=0.2,
        sleep_quality=SleepQuality.GOOD,
        sleep_score=82,
        bedtime="23:00",
        wake_time="06:30"
    ),
    hrv=HeartRateVariability(
        date=date.today(),
        hrv_ms=55.0,
        measured_during_sleep=True
    ),
    rhr=RestingHeartRate(
        date=date.today(),
        rhr_bpm=48
    ),
    training_load=TrainingLoad(
        date=date.today(),
        acute_load=280,
        chronic_load=250,
        body_battery=75
    ),
    calendar_busy_hours=9,
    available_time_slots=["07:00-08:30", "12:30-13:30", "18:00-20:00"]
)
