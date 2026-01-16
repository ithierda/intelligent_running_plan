"""Utilitaires communs pour l'interface"""

# Mapping des jours de la semaine
JOURS_SEMAINE = {
    1: "Lundi",
    2: "Mardi",
    3: "Mercredi",
    4: "Jeudi",
    5: "Vendredi",
    6: "Samedi",
    7: "Dimanche"
}

def get_jour_name(day_of_week: int) -> str:
    """
    Retourne le nom du jour en français
    
    Args:
        day_of_week: Jour de la semaine (1=lundi, 7=dimanche)
        
    Returns:
        Nom du jour en français
    """
    return JOURS_SEMAINE.get(day_of_week, f"Jour {day_of_week}")
