"""Helper pour calculer la charge d'entraînement et ACWR à partir des activités Garmin."""

from datetime import date, timedelta
from typing import List, Dict, Optional


def calculate_training_load_from_activity(activity: Dict) -> float:
    """
    Calcule la charge d'entraînement d'une activité.
    
    Formule simplifiée : Durée (min) × Intensité relative
    Intensité basée sur FC moyenne si disponible, sinon allure.
    
    Args:
        activity: Dictionnaire avec les données d'activité Garmin
        
    Returns:
        Score de charge (Training Stress Score approximatif)
    """
    duration_min = activity.get('duration_minutes', 0)
    
    # Utiliser FC si disponible
    if activity.get('avg_hr'):
        avg_hr = activity['avg_hr']
        max_hr = activity.get('max_hr', 190)  # Estimation si pas de max
        
        # Intensité relative (0-1)
        intensity = avg_hr / max_hr
        
        # Ajustement selon zones
        if intensity < 0.6:  # Zone 1-2 (facile)
            factor = 0.5
        elif intensity < 0.75:  # Zone 3 (tempo)
            factor = 1.0
        elif intensity < 0.85:  # Zone 4 (seuil)
            factor = 1.5
        else:  # Zone 5 (VO2max/sprint)
            factor = 2.0
    else:
        # Fallback sur allure (approximation)
        pace_str = activity.get('pace_str', '6:00')
        try:
            # Parse "5:25" → 5.42 min/km
            parts = pace_str.split(':')
            pace_min_km = float(parts[0]) + float(parts[1]) / 60
            
            # Plus rapide = plus intense
            if pace_min_km < 4.5:  # < 4:30/km = très rapide
                factor = 2.0
            elif pace_min_km < 5.0:  # 4:30-5:00 = seuil
                factor = 1.5
            elif pace_min_km < 5.5:  # 5:00-5:30 = tempo
                factor = 1.0
            else:  # > 5:30 = facile
                factor = 0.5
        except:
            factor = 1.0  # Neutre si erreur
    
    # Charge = Durée × Facteur
    load = duration_min * factor
    
    return round(load, 1)


def calculate_acwr_from_recent_activities(
    last_activity: Dict,
    recent_activities: List[Dict] = None,
    current_date: date = None
) -> Dict:
    """
    Calcule l'ACWR (Acute:Chronic Workload Ratio) simplifié.
    
    ACWR = Charge aiguë (7 derniers jours) / Charge chronique (28 derniers jours)
    
    Args:
        last_activity: Dernière activité du jour
        recent_activities: Liste d'activités récentes (si disponible)
        current_date: Date actuelle
        
    Returns:
        Dict avec acwr, acute_load, chronic_load, status
    """
    if current_date is None:
        current_date = date.today()
    
    # Pour l'instant, calcul simplifié avec juste la dernière activité
    # TODO: Intégrer historique complet Garmin
    
    today_load = calculate_training_load_from_activity(last_activity)
    
    # Estimation approximative (à améliorer avec vrai historique)
    # On considère que la charge hebdo moyenne = 3-4 séances similaires
    estimated_acute = today_load * 3.5  # Estimation semaine
    estimated_chronic = today_load * 3.0 * 4  # Estimation 4 semaines
    
    if estimated_chronic == 0:
        acwr = 1.0
    else:
        acwr = estimated_acute / estimated_chronic
    
    # Déterminer le statut
    if acwr < 0.8:
        status = "Sous-entraîné"
        risk = "faible"
    elif 0.8 <= acwr <= 1.3:
        status = "Optimal"
        risk = "faible"
    elif 1.3 < acwr <= 1.5:
        status = "Attention"
        risk = "modéré"
    else:
        status = "Surcharge"
        risk = "élevé"
    
    return {
        'acwr': round(acwr, 2),
        'today_load': round(today_load, 1),
        'acute_load': round(estimated_acute, 1),
        'chronic_load': round(estimated_chronic, 1),
        'status': status,
        'risk': risk
    }


def adjust_recovery_score_for_activity(
    base_score: float,
    activity_info: Dict,
    hours_since_activity: float
) -> Dict:
    """
    Ajuste le score de récupération en fonction de l'activité récente.
    
    Plus l'activité est récente et intense, plus la pénalité est forte.
    
    Args:
        base_score: Score de récupération de base
        activity_info: Info sur l'activité (load, intensity)
        hours_since_activity: Heures écoulées depuis l'activité
        
    Returns:
        Dict avec adjusted_score, penalty, details
    """
    today_load = activity_info.get('today_load', 0)
    
    # Pénalité basée sur la charge
    if today_load < 30:
        base_penalty = -5  # Activité légère
    elif today_load < 60:
        base_penalty = -10  # Activité modérée
    elif today_load < 100:
        base_penalty = -15  # Activité intense
    else:
        base_penalty = -20  # Activité très intense
    
    # Réduction de la pénalité avec le temps (récupération)
    # Après 24h, pénalité divisée par 2
    time_factor = max(0.3, 1.0 - (hours_since_activity / 48))
    
    penalty = base_penalty * time_factor
    adjusted = base_score + penalty
    adjusted = max(0, min(100, adjusted))
    
    details = [
        f"🏃 Activité ce matin : charge {today_load:.0f}",
        f"⏱️ Il y a {hours_since_activity:.1f}h",
        f"📉 Pénalité fatigue résiduelle : {penalty:.0f} pts"
    ]
    
    return {
        'adjusted_score': round(adjusted, 1),
        'penalty': round(penalty, 1),
        'details': details
    }
