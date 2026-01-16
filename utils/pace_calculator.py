"""
Calculateur d'allures personnalisées basées sur VMA ou objectif de course
"""
from typing import Optional, Tuple


def vma_to_pace(vma_kmh: float) -> str:
    """
    Convertit une VMA en allure (min/km)
    
    Args:
        vma_kmh: VMA en km/h
        
    Returns:
        Allure au format "M:SS" (ex: "4:30")
    """
    # Calculer l'allure en min/km
    pace_min_per_km = 60 / vma_kmh
    
    # Convertir en format "M:SS"
    minutes = int(pace_min_per_km)
    seconds = int((pace_min_per_km - minutes) * 60)
    
    return f"{minutes}:{seconds:02d}"


def pace_to_seconds(pace_str: str) -> int:
    """
    Convertit une allure "M:SS" en secondes totales
    
    Args:
        pace_str: Allure au format "4:30" ou "5:00"
        
    Returns:
        Allure en secondes par km
    """
    parts = pace_str.split(':')
    minutes = int(parts[0])
    seconds = int(parts[1]) if len(parts) > 1 else 0
    return minutes * 60 + seconds


def seconds_to_pace(seconds: int) -> str:
    """
    Convertit des secondes en allure "M:SS"
    
    Args:
        seconds: Secondes par km
        
    Returns:
        Allure au format "4:30"
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def calculate_training_paces_from_vma(
    vma_kmh: float, 
    fc_max: int = None, 
    fc_repos: int = None, 
    level: str = "Intermédiaire",
    target_pace_min_per_km: float = None,
    distance_km: float = None
) -> dict:
    """
    Calcule toutes les allures d'entraînement basées sur VMA
    
    NOUVELLE APPROCHE : Si objectif fourni, calcule l'écart entre VMA et objectif
    pour ajuster les zones d'entraînement de manière intelligente.
    
    Logique :
    - Si objectif proche de la VMA (race > 90% VMA) → athlète ambitieux → EF plus lente (65%)
    - Si objectif loin de la VMA (race < 85% VMA) → athlète prudent → EF plus rapide (70%)
    
    Args:
        vma_kmh: VMA en km/h
        fc_max: Fréquence cardiaque maximale (optionnel)
        fc_repos: Fréquence cardiaque de repos (optionnel)
        level: Niveau d'entraînement (optionnel, pour backward compatibility)
        target_pace_min_per_km: Allure cible en min/km (optionnel mais recommandé)
        distance_km: Distance de course en km (optionnel mais recommandé)
        
    Returns:
        Dict avec toutes les allures d'entraînement
    """
    vma_pace = vma_to_pace(vma_kmh)
    
    # Calculer le % VMA de l'objectif si fourni
    race_vma_percent = None
    if target_pace_min_per_km and distance_km:
        # Convertir l'allure cible en vitesse (km/h)
        target_speed_kmh = 60 / target_pace_min_per_km
        race_vma_percent = (target_speed_kmh / vma_kmh) * 100
        
        # Ajuster les zones selon l'écart VMA/objectif
        # ET selon FC repos (athlètes avec FC repos basse ont meilleure efficacité)
        if race_vma_percent >= 95:
            # Objectif très ambitieux (ex: Sub 18 avec VMA 19) → EF très lente
            easy_base = 0.58
            recovery_base = 0.53
        elif race_vma_percent >= 90:
            # Objectif ambitieux (ex: Sub 20 avec VMA 17) → EF lente
            easy_base = 0.60
            recovery_base = 0.55
        elif race_vma_percent >= 85:
            # Objectif réaliste (ex: Sub 20 avec VMA 18) → EF modérée
            easy_base = 0.63
            recovery_base = 0.58
        else:
            # Objectif conservateur (ex: Sub 20 avec VMA 19) → EF rapide
            easy_base = 0.66
            recovery_base = 0.60
        
        # Ajustement supplémentaire pour FC repos très basse (<48)
        if fc_repos and fc_repos < 48:
            easy_base -= 0.03  # -3% VMA supplémentaire
            recovery_base -= 0.03
            print(f"[DEBUG] Ajustement FC repos bas ({fc_repos} bpm): -3% VMA")
        
        print(f"[DEBUG] Objectif: {target_pace_min_per_km:.2f} min/km = {target_speed_kmh:.2f} km/h = {race_vma_percent:.1f}% VMA")
        print(f"[DEBUG] Easy base ajusté: {easy_base*100:.0f}% VMA, Recovery: {recovery_base*100:.0f}% VMA")
    else:
        # Pas d'objectif fourni : utiliser valeurs par défaut avec ajustement FC
        level_str = str(level).lower() if level else ""
        is_advanced = "avanc" in level_str
        has_low_hr = fc_repos and fc_repos < 50
        
        if is_advanced and has_low_hr:
            easy_base = 0.62
            recovery_base = 0.58
            print(f"[DEBUG] Mode avancé (FC repos bas): Easy {easy_base*100:.0f}% VMA")
        else:
            easy_base = 0.69
            recovery_base = 0.65
            print(f"[DEBUG] Mode standard: Easy {easy_base*100:.0f}% VMA")
    
    return {
        'recovery': {
            'min': vma_to_pace(vma_kmh * recovery_base),
            'max': vma_to_pace(vma_kmh * (recovery_base + 0.05)),
            'target': vma_to_pace(vma_kmh * (recovery_base + 0.02))
        },
        'easy': {
            'min': vma_to_pace(vma_kmh * easy_base),
            'max': vma_to_pace(vma_kmh * (easy_base + 0.05)),
            'target': vma_to_pace(vma_kmh * (easy_base + 0.02))
        },
        'endurance': {
            'min': vma_to_pace(vma_kmh * 0.75),
            'max': vma_to_pace(vma_kmh * 0.80),
            'target': vma_to_pace(vma_kmh * 0.77)
        },
        'tempo': {
            'min': vma_to_pace(vma_kmh * 0.85),
            'max': vma_to_pace(vma_kmh * 0.88),
            'target': vma_to_pace(vma_kmh * 0.86)
        },
        'threshold': {
            'min': vma_to_pace(vma_kmh * 0.88),
            'max': vma_to_pace(vma_kmh * 0.92),
            'target': vma_to_pace(vma_kmh * 0.90)
        },
        'semi_race': {
            'min': vma_to_pace(vma_kmh * 0.88),
            'max': vma_to_pace(vma_kmh * 0.90),
            'target': vma_to_pace(vma_kmh * 0.89)
        },
        '10k_race': {
            'min': vma_to_pace(vma_kmh * 0.92),
            'max': vma_to_pace(vma_kmh * 0.95),
            'target': vma_to_pace(vma_kmh * 0.93)
        },
        '5k_race': {
            'min': vma_to_pace(vma_kmh * 0.95),
            'max': vma_to_pace(vma_kmh * 0.98),
            'target': vma_to_pace(vma_kmh * 0.96)
        },
        'vma': {
            'min': vma_to_pace(vma_kmh * 1.00),
            'max': vma_to_pace(vma_kmh * 1.05),
            'target': vma_to_pace(vma_kmh * 1.00)
        }
    }


def calculate_training_paces_from_target(
    target_time_minutes: float,
    distance_km: float
) -> dict:
    """
    Calcule les allures d'entraînement UNIQUEMENT depuis l'objectif de course
    (pour les athlètes sans VMA connue)
    
    Règles d'entraînement classiques :
    - Recovery: allure course + 90-120 sec/km
    - Easy (EF): allure course + 60-90 sec/km
    - Endurance: allure course + 30-45 sec/km
    - Tempo: allure course + 15-20 sec/km
    - Threshold: allure course + 5-10 sec/km
    - Race: allure objectif
    - Intervals: allure course - 5 à -15 sec/km (selon distance)
    
    Args:
        target_time_minutes: Objectif en minutes
        distance_km: Distance de la course en km
        
    Returns:
        Dict avec toutes les allures au même format que calculate_training_paces_from_vma
    """
    # Allure cible en sec/km
    target_pace_sec_per_km = (target_time_minutes * 60) / distance_km
    
    def add_seconds_to_pace(pace_sec, delta_sec):
        """Ajoute des secondes à une allure"""
        new_pace_sec = pace_sec + delta_sec
        mins = int(new_pace_sec // 60)
        secs = int(new_pace_sec % 60)
        return f"{mins}:{secs:02d}"
    
    # Calculer toutes les zones
    recovery_target = add_seconds_to_pace(target_pace_sec_per_km, 105)
    recovery_min = add_seconds_to_pace(target_pace_sec_per_km, 90)
    recovery_max = add_seconds_to_pace(target_pace_sec_per_km, 120)
    
    easy_target = add_seconds_to_pace(target_pace_sec_per_km, 75)
    easy_min = add_seconds_to_pace(target_pace_sec_per_km, 60)
    easy_max = add_seconds_to_pace(target_pace_sec_per_km, 90)
    
    endurance_target = add_seconds_to_pace(target_pace_sec_per_km, 37)
    endurance_min = add_seconds_to_pace(target_pace_sec_per_km, 30)
    endurance_max = add_seconds_to_pace(target_pace_sec_per_km, 45)
    
    tempo_target = add_seconds_to_pace(target_pace_sec_per_km, 17)
    tempo_min = add_seconds_to_pace(target_pace_sec_per_km, 15)
    tempo_max = add_seconds_to_pace(target_pace_sec_per_km, 20)
    
    threshold_target = add_seconds_to_pace(target_pace_sec_per_km, 7)
    threshold_min = add_seconds_to_pace(target_pace_sec_per_km, 5)
    threshold_max = add_seconds_to_pace(target_pace_sec_per_km, 10)
    
    race_target = add_seconds_to_pace(target_pace_sec_per_km, 0)
    
    # Intervalles selon la distance
    if distance_km <= 5:
        interval_delta = -5
    elif distance_km <= 10:
        interval_delta = -8
    else:
        interval_delta = -10
    
    interval_target = add_seconds_to_pace(target_pace_sec_per_km, interval_delta)
    interval_min = add_seconds_to_pace(target_pace_sec_per_km, interval_delta - 5)
    interval_max = add_seconds_to_pace(target_pace_sec_per_km, interval_delta + 5)
    
    return {
        'recovery': {
            'min': recovery_min,
            'max': recovery_max,
            'target': recovery_target
        },
        'easy': {
            'min': easy_min,
            'max': easy_max,
            'target': easy_target
        },
        'endurance': {
            'min': endurance_min,
            'max': endurance_max,
            'target': endurance_target
        },
        'tempo': {
            'min': tempo_min,
            'max': tempo_max,
            'target': tempo_target
        },
        'threshold': {
            'min': threshold_min,
            'max': threshold_max,
            'target': threshold_target
        },
        'semi_race': {
            'min': race_target,
            'max': race_target,
            'target': race_target
        },
        '10k_race': {
            'min': race_target,
            'max': race_target,
            'target': race_target
        },
        '5k_race': {
            'min': race_target,
            'max': race_target,
            'target': race_target
        },
        'vma': {
            'min': interval_min,
            'max': interval_max,
            'target': interval_target
        }
    }


def estimate_race_time(distance_km: float, vma_kmh: float) -> Tuple[int, str]:
    """
    Estime un temps de course basé sur VMA
    
    Formules approximatives:
    - 5km: ~96% VMA
    - 10km: ~93% VMA
    - Semi: ~89% VMA
    - Marathon: ~82% VMA
    
    Args:
        distance_km: Distance de la course en km
        vma_kmh: VMA de l'athlète en km/h
        
    Returns:
        Tuple (temps en minutes, temps formaté "H:MM:SS")
    """
    # Déterminer le % de VMA selon la distance
    if distance_km <= 5:
        vma_percentage = 0.96
    elif distance_km <= 10:
        vma_percentage = 0.93
    elif distance_km <= 21.1:
        vma_percentage = 0.89
    elif distance_km <= 42.2:
        vma_percentage = 0.82
    else:
        vma_percentage = 0.75  # Ultra
    
    # Vitesse de course en km/h
    race_speed_kmh = vma_kmh * vma_percentage
    
    # Temps en heures
    time_hours = distance_km / race_speed_kmh
    
    # Convertir en minutes et formater
    time_minutes = int(time_hours * 60)
    
    hours = int(time_hours)
    remaining_minutes = int((time_hours - hours) * 60)
    seconds = int(((time_hours - hours) * 60 - remaining_minutes) * 60)
    
    if hours > 0:
        time_str = f"{hours}:{remaining_minutes:02d}:{seconds:02d}"
    else:
        time_str = f"{remaining_minutes}:{seconds:02d}"
    
    return time_minutes, time_str


def calculate_heart_rate_zones(max_hr: int, resting_hr: Optional[int] = None) -> dict:
    """
    Calcule les zones de fréquence cardiaque
    
    Méthode 1 (si FC repos connue): Karvonen (réserve cardiaque)
    Méthode 2 (sinon): % de FC max
    
    Args:
        max_hr: Fréquence cardiaque maximale
        resting_hr: Fréquence cardiaque au repos (optionnel)
        
    Returns:
        Dict avec les 5 zones cardiaques
    """
    if resting_hr:
        # Méthode Karvonen (plus précise)
        hr_reserve = max_hr - resting_hr
        
        zones = {
            'Z1_recovery': {
                'min': int(resting_hr + hr_reserve * 0.50),
                'max': int(resting_hr + hr_reserve * 0.60),
                'description': 'Récupération active'
            },
            'Z2_endurance': {
                'min': int(resting_hr + hr_reserve * 0.60),
                'max': int(resting_hr + hr_reserve * 0.70),
                'description': 'Endurance fondamentale'
            },
            'Z3_tempo': {
                'min': int(resting_hr + hr_reserve * 0.70),
                'max': int(resting_hr + hr_reserve * 0.80),
                'description': 'Tempo / Endurance active'
            },
            'Z4_threshold': {
                'min': int(resting_hr + hr_reserve * 0.80),
                'max': int(resting_hr + hr_reserve * 0.90),
                'description': 'Seuil anaérobie'
            },
            'Z5_vo2max': {
                'min': int(resting_hr + hr_reserve * 0.90),
                'max': max_hr,
                'description': 'VO2max / VMA'
            }
        }
    else:
        # Méthode % FC max (standard)
        zones = {
            'Z1_recovery': {
                'min': int(max_hr * 0.50),
                'max': int(max_hr * 0.60),
                'description': 'Récupération active'
            },
            'Z2_endurance': {
                'min': int(max_hr * 0.60),
                'max': int(max_hr * 0.70),
                'description': 'Endurance fondamentale'
            },
            'Z3_tempo': {
                'min': int(max_hr * 0.70),
                'max': int(max_hr * 0.80),
                'description': 'Tempo / Endurance active'
            },
            'Z4_threshold': {
                'min': int(max_hr * 0.80),
                'max': int(max_hr * 0.90),
                'description': 'Seuil anaérobie'
            },
            'Z5_vo2max': {
                'min': int(max_hr * 0.90),
                'max': max_hr,
                'description': 'VO2max / VMA'
            }
        }
    
    return zones


def suggest_race_objective(distance_km: float, vma_kmh: float) -> str:
    """
    Suggère un objectif de temps réaliste basé sur VMA
    
    Args:
        distance_km: Distance de la course
        vma_kmh: VMA de l'athlète
        
    Returns:
        Suggestion d'objectif (ex: "Sub 1:45", "Sub 45min")
    """
    time_minutes, time_str = estimate_race_time(distance_km, vma_kmh)
    
    # Arrondir à des objectifs standards
    if distance_km <= 5:
        # 5km: objectifs par tranches de 1min
        targets = [18, 20, 22, 25, 30]
        for target in targets:
            if time_minutes <= target + 1:
                return f"Sub {target}min"
        return f"Finir (≈{time_str})"
        
    elif distance_km <= 10:
        # 10km: objectifs par tranches de 2-5min
        targets = [35, 40, 45, 50, 60]
        for target in targets:
            if time_minutes <= target + 2:
                return f"Sub {target}min"
        return f"Finir (≈{time_str})"
        
    elif distance_km <= 21.1:
        # Semi: objectifs par tranches de 5min
        targets = [90, 95, 100, 105, 110, 120]  # 1:30, 1:35, 1:40, 1:45, 1:50, 2:00
        target_labels = ["1:30", "1:35", "1:40", "1:45", "1:50", "2:00"]
        
        for i, target in enumerate(targets):
            if time_minutes <= target + 2:
                return f"Sub {target_labels[i]}"
        return f"Finir (≈{time_str})"
        
    else:
        # Marathon et +
        hours = time_minutes // 60
        return f"≈{time_str}"
