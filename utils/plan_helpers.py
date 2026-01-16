"""Fonctions utilitaires pour manipuler les plans d'entraînement."""

from datetime import date
from typing import Optional
from models.training_plan import TrainingPlan
from models.session import TrainingSession


def get_session_for_date(plan: TrainingPlan, target_date: date) -> Optional[TrainingSession]:
    """
    Récupère la séance prévue pour une date donnée.
    
    Args:
        plan: Le plan d'entraînement complet
        target_date: La date pour laquelle on veut la séance
        
    Returns:
        TrainingSession si une séance est prévue ce jour, None sinon
    """
    # Calculer le nombre de jours depuis le début du plan
    days_since_start = (target_date - plan.start_date).days
    
    # Si on est avant le début ou après la fin du plan
    if days_since_start < 0 or days_since_start >= len(plan.weeks) * 7:
        return None
    
    # Trouver la semaine correspondante
    week_index = days_since_start // 7
    day_in_week = days_since_start % 7
    
    if week_index >= len(plan.weeks):
        return None
    
    week = plan.weeks[week_index]
    
    # Trouver la séance du jour (si elle existe)
    if day_in_week < len(week.sessions):
        return week.sessions[day_in_week]
    
    return None


def get_current_week_number(plan: TrainingPlan, target_date: date) -> Optional[int]:
    """
    Retourne le numéro de semaine (1-indexed) pour une date donnée.
    
    Returns:
        Numéro de semaine (1 à 12), ou None si hors plan
    """
    days_since_start = (target_date - plan.start_date).days
    
    if days_since_start < 0 or days_since_start >= len(plan.weeks) * 7:
        return None
    
    return (days_since_start // 7) + 1


def get_week_summary(plan: TrainingPlan, week_number: int) -> dict:
    """
    Retourne un résumé de la semaine (distance totale, nombre de séances, etc.).
    
    Args:
        plan: Le plan d'entraînement
        week_number: Numéro de semaine (1-indexed)
        
    Returns:
        Dictionnaire avec les statistiques de la semaine
    """
    if week_number < 1 or week_number > len(plan.weeks):
        return {}
    
    week = plan.weeks[week_number - 1]
    
    total_distance = sum(s.distance_km for s in week.sessions)
    total_duration = sum(s.duration_minutes for s in week.sessions)
    key_sessions = sum(1 for s in week.sessions if s.is_key_session)
    
    return {
        'week_number': week_number,
        'phase': week.phase.value,
        'week_type': week.week_type.value,
        'total_distance': total_distance,
        'total_duration': total_duration,
        'num_sessions': len(week.sessions),
        'key_sessions': key_sessions
    }
