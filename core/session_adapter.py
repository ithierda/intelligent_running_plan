"""
Moteur d'adaptation intelligente des séances d'entraînement
"""
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from enum import Enum

from models import (
    TrainingSession, DailyMetrics, SessionType, SessionIntensity,
    SessionStatus, ReadinessLevel
)
from config.settings import RECOVERY_THRESHOLDS, ACWR_OPTIMAL_MIN, ACWR_OPTIMAL_MAX


class AdaptationAction(str, Enum):
    """Actions possibles d'adaptation"""
    MAINTAIN = "Maintenir"
    MONITOR = "Maintenir avec surveillance"
    REDUCE = "Alléger"
    REPLACE = "Remplacer"
    POSTPONE = "Reporter"
    CANCEL = "Annuler"


class AdaptationRecommendation:
    """Recommandation d'adaptation d'une séance"""
    
    def __init__(
        self,
        action: AdaptationAction,
        reason: str,
        details: list[str],
        modified_session: Optional[TrainingSession] = None,
        confidence: float = 1.0
    ):
        self.action = action
        self.reason = reason
        self.details = details  # Liste des facteurs pris en compte
        self.modified_session = modified_session
        self.confidence = confidence  # 0-1
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return {
            'action': self.action.value,
            'reason': self.reason,
            'details': self.details,
            'confidence': self.confidence,
            'has_modified_session': self.modified_session is not None
        }


class SessionAdapter:
    """
    Adaptateur intelligent de séances d'entraînement
    
    Prend en compte:
    - Score de récupération (sommeil, HRV, FC repos, charge)
    - Disponibilité calendrier
    - Météo (futur)
    - Historique récent
    """
    
    def __init__(self):
        self.thresholds = RECOVERY_THRESHOLDS
    
    def adapt_session(
        self,
        session: TrainingSession,
        metrics: DailyMetrics,
        upcoming_sessions: list[TrainingSession] = None,
        recent_sessions: list[TrainingSession] = None
    ) -> AdaptationRecommendation:
        """
        Adapte une séance en fonction des métriques du jour
        
        Args:
            session: Séance planifiée
            metrics: Métriques du jour
            upcoming_sessions: Prochaines séances (pour optimisation)
            recent_sessions: Séances récentes (pour contexte)
        
        Returns:
            AdaptationRecommendation
        """
        # 1. Calculer le score de récupération si pas déjà fait
        if metrics.recovery_score is None:
            metrics.calculate_recovery_score()
        
        recovery_score = metrics.recovery_score or 50.0
        details = []
        
        # 2. Analyser les différents facteurs
        recovery_factor = self._analyze_recovery(recovery_score, metrics, details)
        availability_factor = self._analyze_availability(session, metrics, details)
        load_factor = self._analyze_training_load(metrics, recent_sessions, details)
        sequence_factor = self._analyze_sequence(session, recent_sessions, upcoming_sessions, details)
        
        # 3. Décider de l'action
        action, reason, modified = self._decide_action(
            session=session,
            recovery_score=recovery_score,
            recovery_factor=recovery_factor,
            availability_factor=availability_factor,
            load_factor=load_factor,
            sequence_factor=sequence_factor
        )
        
        # 4. Calculer la confiance
        confidence = self._calculate_confidence(metrics)
        
        return AdaptationRecommendation(
            action=action,
            reason=reason,
            details=details,
            modified_session=modified,
            confidence=confidence
        )
    
    def _analyze_recovery(
        self,
        recovery_score: float,
        metrics: DailyMetrics,
        details: list[str]
    ) -> float:
        """
        Analyse le score de récupération
        Returns: facteur 0-1 (1 = optimal)
        """
        # Ajouter détails
        details.append(f"💤 Score de récupération: {recovery_score:.0f}/100 ({metrics.readiness_level.value if metrics.readiness_level else 'N/A'})")
        
        if metrics.sleep:
            details.append(f"🛌 Sommeil: {metrics.sleep.total_sleep_hours:.1f}h (qualité: {metrics.sleep.sleep_quality.value})")
        
        if metrics.hrv:
            details.append(f"❤️ VFC: {metrics.hrv.hrv_ms:.0f}ms")
        
        if metrics.training_load and metrics.training_load.acwr:
            details.append(f"📊 ACWR: {metrics.training_load.acwr:.2f} ({metrics.training_load.get_fatigue_status()})")
        
        return recovery_score / 100.0
    
    def _analyze_availability(
        self,
        session: TrainingSession,
        metrics: DailyMetrics,
        details: list[str]
    ) -> float:
        """
        Analyse la disponibilité dans le calendrier
        Returns: facteur 0-1 (1 = parfaite dispo)
        """
        if not metrics.available_time_slots:
            details.append("📅 Agenda: Pas de données de disponibilité")
            return 0.5  # Neutre si pas d'info
        
        # Vérifier s'il y a assez de temps
        has_time = metrics.has_available_time(session.duration_minutes + 30)  # +30min marge
        
        if has_time:
            details.append(f"✅ Agenda: {len(metrics.available_time_slots)} créneaux disponibles")
            return 1.0
        else:
            details.append(f"⚠️ Agenda: Créneaux limités ({metrics.calendar_busy_hours}h occupées)")
            return 0.3
    
    def _analyze_training_load(
        self,
        metrics: DailyMetrics,
        recent_sessions: Optional[list[TrainingSession]],
        details: list[str]
    ) -> float:
        """
        Analyse la charge d'entraînement récente
        Returns: facteur 0-1 (1 = charge optimale)
        """
        if not metrics.training_load or not metrics.training_load.acwr:
            return 0.7  # Neutre
        
        acwr = metrics.training_load.acwr
        
        # ACWR optimal entre 0.8 et 1.3
        if ACWR_OPTIMAL_MIN <= acwr <= ACWR_OPTIMAL_MAX:
            return 1.0
        elif acwr < ACWR_OPTIMAL_MIN:
            # Sous-entraîné: peut charger davantage
            return 0.9
        elif acwr <= 1.5:
            # Légèrement surchargé
            return 0.6
        else:
            # Fortement surchargé
            return 0.3
    
    def _analyze_sequence(
        self,
        session: TrainingSession,
        recent_sessions: Optional[list[TrainingSession]],
        upcoming_sessions: Optional[list[TrainingSession]],
        details: list[str]
    ) -> float:
        """
        Analyse l'enchaînement des séances
        Returns: facteur 0-1
        """
        if not recent_sessions:
            return 1.0
        
        # Vérifier les dernières 48h
        last_48h = [
            s for s in recent_sessions
            if s.completed_at and (datetime.now() - s.completed_at).days <= 2
        ]
        
        # Compter les séances intenses récentes
        intense_recent = sum(
            1 for s in last_48h
            if s.intensity in [SessionIntensity.HARD, SessionIntensity.VERY_HARD]
        )
        
        if intense_recent >= 2 and session.intensity in [SessionIntensity.HARD, SessionIntensity.VERY_HARD]:
            details.append("⚠️ Enchaînement: 2+ séances intenses dans les 48h")
            return 0.4
        elif intense_recent == 1 and session.intensity == SessionIntensity.VERY_HARD:
            details.append("ℹ️ Enchaînement: 1 séance intense récente")
            return 0.7
        else:
            return 1.0
    
    def _decide_action(
        self,
        session: TrainingSession,
        recovery_score: float,
        recovery_factor: float,
        availability_factor: float,
        load_factor: float,
        sequence_factor: float
    ) -> Tuple[AdaptationAction, str, Optional[TrainingSession]]:
        """
        Décide de l'action à prendre
        
        Returns:
            (action, reason, modified_session)
        """
        # Score composite pondéré
        composite_score = (
            recovery_factor * 0.40 +
            load_factor * 0.25 +
            sequence_factor * 0.20 +
            availability_factor * 0.15
        ) * 100
        
        # Séances clés: plus de tolérance
        if session.is_key_session:
            threshold_adjust = -5  # Baisser les seuils de 5 points
        else:
            threshold_adjust = 0
        
        # Décision basée sur le score composite
        modified_session = None
        
        # 1. Score excellent: MAINTENIR
        if composite_score >= (self.thresholds['excellent'] + threshold_adjust):
            return (
                AdaptationAction.MAINTAIN,
                "✅ Conditions optimales pour la séance planifiée",
                None
            )
        
        # 2. Score bon: MAINTENIR AVEC SURVEILLANCE
        elif composite_score >= (self.thresholds['good'] + threshold_adjust):
            return (
                AdaptationAction.MONITOR,
                "👍 Conditions bonnes, surveiller les signes de fatigue pendant la séance",
                None
            )
        
        # 3. Score moyen: ALLÉGER
        elif composite_score >= (self.thresholds['moderate'] + threshold_adjust):
            modified_session = self._lighten_session(session, reduction=0.75)
            return (
                AdaptationAction.REDUCE,
                "⚠️ Récupération moyenne: séance allégée de 25%",
                modified_session
            )
        
        # 4. Score faible: REMPLACER
        elif composite_score >= (self.thresholds['poor'] + threshold_adjust):
            # Si séance intense, remplacer par endurance légère
            if session.intensity in [SessionIntensity.HARD, SessionIntensity.VERY_HARD]:
                modified_session = self._replace_with_easy(session)
                return (
                    AdaptationAction.REPLACE,
                    "⚠️ Faible récupération: séance intense remplacée par endurance légère",
                    modified_session
                )
            else:
                modified_session = self._lighten_session(session, reduction=0.6)
                return (
                    AdaptationAction.REDUCE,
                    "⚠️ Faible récupération: séance allégée de 40%",
                    modified_session
                )
        
        # 5. Score très faible ou conflit calendrier majeur
        else:
            if availability_factor < 0.4 and session.can_be_postponed:
                return (
                    AdaptationAction.POSTPONE,
                    "📅 Conflit d'agenda: reporter la séance à un autre jour",
                    None
                )
            else:
                return (
                    AdaptationAction.CANCEL,
                    "🛑 Récupération insuffisante: repos complet recommandé",
                    None
                )
    
    def _lighten_session(
        self,
        session: TrainingSession,
        reduction: float = 0.75
    ) -> TrainingSession:
        """
        Allège une séance (réduit durée/distance)
        reduction: 0.75 = garde 75% (réduit de 25%)
        """
        # Créer une copie
        modified = session.model_copy(deep=True)
        modified.id = f"{session.id}_adapted"
        modified.status = SessionStatus.ADAPTED
        modified.adaptation_reason = f"Séance allégée à {int(reduction*100)}% du volume"
        
        # Réduire durée et distance
        modified.duration_minutes = int(modified.duration_minutes * reduction)
        if modified.distance_km:
            modified.distance_km = round(modified.distance_km * reduction, 1)
        
        # Réduire chaque portion de la structure
        for zone in modified.structure:
            if zone.duration_minutes:
                zone.duration_minutes = int(zone.duration_minutes * reduction)
            if zone.distance_km:
                zone.distance_km = round(zone.distance_km * reduction, 2)
        
        # Baisser légèrement l'intensité
        if modified.intensity == SessionIntensity.VERY_HARD:
            modified.intensity = SessionIntensity.HARD
        elif modified.intensity == SessionIntensity.HARD:
            modified.intensity = SessionIntensity.MODERATE
        
        return modified
    
    def _replace_with_easy(self, session: TrainingSession) -> TrainingSession:
        """Remplace une séance intense par de l'endurance facile"""
        from models.session import PaceZone
        
        modified = session.model_copy(deep=True)
        modified.id = f"{session.id}_easy"
        modified.session_type = SessionType.RECOVERY
        modified.intensity = SessionIntensity.EASY
        modified.status = SessionStatus.ADAPTED
        modified.adaptation_reason = "Séance intense remplacée par récupération active"
        modified.title = f"Récupération active (remplace {session.title})"
        modified.description = "Course facile de récupération"
        
        # Durée réduite, allure très facile
        modified.duration_minutes = min(40, int(session.duration_minutes * 0.6))
        modified.distance_km = 6.0
        
        # Structure simple
        modified.structure = [
            PaceZone(
                description="Endurance très facile",
                duration_minutes=modified.duration_minutes,
                pace_min_per_km="6:15",
                pace_max_per_km="6:30",
                hr_zone="70-75% FCmax"
            )
        ]
        
        return modified
    
    def _calculate_confidence(self, metrics: DailyMetrics) -> float:
        """
        Calcule la confiance dans la recommandation
        Basée sur la complétude des données
        """
        data_points = 0
        total_points = 5
        
        if metrics.sleep:
            data_points += 1
        if metrics.hrv:
            data_points += 1
        if metrics.training_load:
            data_points += 1
        if metrics.available_time_slots:
            data_points += 1
        if metrics.subjective:
            data_points += 1
        
        return data_points / total_points


def quick_adapt(
    session: TrainingSession,
    recovery_score: float,
    has_time: bool = True
) -> AdaptationRecommendation:
    """
    Fonction utilitaire pour adaptation rapide sans toutes les métriques
    
    Args:
        session: Séance à adapter
        recovery_score: Score 0-100
        has_time: Disponibilité dans l'agenda
    
    Returns:
        AdaptationRecommendation
    """
    # Créer des métriques minimales
    from models import DailyMetrics, ReadinessLevel
    
    metrics = DailyMetrics(
        date=date.today(),
        recovery_score=recovery_score,
        available_time_slots=["18:00-20:00"] if has_time else []
    )
    
    # Déterminer readiness level
    if recovery_score >= 85:
        metrics.readiness_level = ReadinessLevel.OPTIMAL
    elif recovery_score >= 70:
        metrics.readiness_level = ReadinessLevel.GOOD
    elif recovery_score >= 55:
        metrics.readiness_level = ReadinessLevel.OK
    elif recovery_score >= 40:
        metrics.readiness_level = ReadinessLevel.COMPROMISED
    else:
        metrics.readiness_level = ReadinessLevel.POOR
    
    adapter = SessionAdapter()
    return adapter.adapt_session(session, metrics)
