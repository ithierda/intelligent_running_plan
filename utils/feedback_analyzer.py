"""Analyseur de feedbacks d'activités pour ajuster la récupération."""

from typing import Dict, List, Optional


# Impacts des feedbacks négatifs (soustraction de points)
NEGATIVE_IMPACTS = {
    'jambes_lourdes': -10,      # Fatigue musculaire importante
    'enrhume': -15,              # Maladie = repos nécessaire
    'fatigue': -12,              # Fatigue générale
    'douleurs': -8,              # Courbatures/douleurs
    'mauvaise_journee': -5,      # Impact psychologique
    'pluie': -2,                 # Conditions difficiles (léger impact)
    'chaleur': -5,               # Déshydratation, effort supplémentaire
    'froid': -3,                 # Conditions difficiles
}

# Impacts des feedbacks positifs (ajout de points)
POSITIVE_IMPACTS = {
    'kiffe': 8,                  # Excellent moral = boost récupération
    'jambes_legeres': 10,        # Excellente forme physique
    'bonne_forme': 8,            # Bonne condition
    'mental_top': 6,             # Bon état psychologique
    'plaisir': 5,                # Motivation élevée
}


def analyze_activity_feedback(feedback: Dict) -> Dict:
    """
    Analyse un feedback d'activité et calcule son impact sur la récupération.
    
    Args:
        feedback: Dictionnaire avec 'positive', 'negative', 'notes'
        
    Returns:
        Dictionnaire avec 'score_adjustment', 'details', 'warnings'
    """
    adjustment = 0
    details = []
    warnings = []
    
    # Analyser les feedbacks positifs
    if 'positive' in feedback and feedback['positive']:
        for item in feedback['positive']:
            if item in POSITIVE_IMPACTS:
                points = POSITIVE_IMPACTS[item]
                adjustment += points
                details.append(f"✅ {item.replace('_', ' ').title()}: +{points} pts")
    
    # Analyser les feedbacks négatifs
    if 'negative' in feedback and feedback['negative']:
        for item in feedback['negative']:
            if item in NEGATIVE_IMPACTS:
                points = NEGATIVE_IMPACTS[item]
                adjustment += points  # Déjà négatif
                details.append(f"⚠️ {item.replace('_', ' ').title()}: {points} pts")
                
                # Ajouter des warnings spécifiques
                if item == 'enrhume':
                    warnings.append("🤧 Maladie détectée : privilégiez le repos complet")
                elif item == 'douleurs':
                    warnings.append("😣 Douleurs signalées : évitez les séances intenses")
                elif item == 'jambes_lourdes':
                    warnings.append("🦵 Fatigue musculaire : séance régénérative recommandée")
    
    return {
        'score_adjustment': adjustment,
        'details': details,
        'warnings': warnings
    }


def get_recent_feedback_impact(
    feedbacks: List[Dict],
    days_lookback: int = 2
) -> Dict:
    """
    Calcule l'impact des feedbacks récents (derniers jours).
    
    Args:
        feedbacks: Liste des feedbacks (plus récent en premier)
        days_lookback: Nombre de jours à considérer
        
    Returns:
        Dictionnaire avec impact cumulé
    """
    if not feedbacks:
        return {
            'score_adjustment': 0,
            'details': [],
            'warnings': []
        }
    
    # Prendre seulement les N derniers feedbacks
    recent = feedbacks[:days_lookback]
    
    total_adjustment = 0
    all_details = []
    all_warnings = []
    
    for i, feedback in enumerate(recent):
        result = analyze_activity_feedback(feedback)
        
        # Dépréciation dans le temps (plus récent = plus d'impact)
        decay_factor = 1.0 - (i * 0.3)  # J-1: 100%, J-2: 70%
        adjusted_score = result['score_adjustment'] * decay_factor
        
        total_adjustment += adjusted_score
        
        if result['details']:
            day_label = "Hier" if i == 0 else f"Il y a {i+1} jours"
            all_details.append(f"📅 {day_label}:")
            all_details.extend([f"  {d}" for d in result['details']])
        
        all_warnings.extend(result['warnings'])
    
    return {
        'score_adjustment': round(total_adjustment, 1),
        'details': all_details,
        'warnings': list(set(all_warnings))  # Dédupliquer
    }


def should_force_rest(feedbacks: List[Dict]) -> bool:
    """
    Détermine si les feedbacks indiquent un besoin impératif de repos.
    
    Returns:
        True si repos obligatoire
    """
    if not feedbacks:
        return False
    
    # Vérifier le dernier feedback
    last = feedbacks[0] if feedbacks else {}
    
    # Conditions de repos forcé
    force_rest_conditions = {
        'enrhume',      # Maladie
        'douleurs',     # Douleurs importantes
    }
    
    negative = set(last.get('negative', []))
    
    # Si maladie OU (jambes lourdes + fatigue)
    if negative & force_rest_conditions:
        return True
    
    if 'jambes_lourdes' in negative and 'fatigue' in negative:
        return True
    
    return False


def get_feedback_summary_for_display(feedbacks: List[Dict], max_display: int = 5) -> str:
    """
    Génère un résumé textuel des feedbacks pour affichage.
    
    Returns:
        String formaté pour affichage
    """
    if not feedbacks:
        return "Aucun feedback enregistré"
    
    lines = []
    for i, fb in enumerate(feedbacks[:max_display]):
        date = fb.get('activity_date', 'Date inconnue')
        positive = fb.get('positive', [])
        negative = fb.get('negative', [])
        
        sentiment = "😊" if len(positive) > len(negative) else "😓" if negative else "😐"
        
        items = []
        if positive:
            items.append(f"+{len(positive)} positif(s)")
        if negative:
            items.append(f"{len(negative)} négatif(s)")
        
        lines.append(f"{sentiment} {date}: {', '.join(items) if items else 'Neutre'}")
    
    return "\n".join(lines)
