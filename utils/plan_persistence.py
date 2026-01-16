"""Utilitaires pour sauvegarder et charger le plan d'entraînement."""

import json
from pathlib import Path
from datetime import date
from typing import Optional

from models.training_plan import TrainingPlan, TrainingWeek, TrainingPhase, WeekType
from models.session import TrainingSession, SessionType, SessionIntensity, SessionStatus, PaceZone


def save_plan_to_json(plan: TrainingPlan, filepath: str = "data/training_plan.json"):
    """
    Sauvegarde le plan d'entraînement au format JSON.
    
    Args:
        plan: Plan d'entraînement à sauvegarder
        filepath: Chemin du fichier JSON
    """
    # Créer le dossier si nécessaire
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convertir en dict sérialisable
    plan_dict = {
        'id': plan.id,
        'name': plan.name,
        'description': plan.description,
        'goal_distance': plan.goal_distance,
        'goal_time': plan.goal_time,
        'target_pace_per_km': plan.target_pace_per_km,
        'start_date': plan.start_date.isoformat(),
        'end_date': plan.end_date.isoformat(),
        'duration_weeks': plan.duration_weeks,
        'sessions_per_week': plan.sessions_per_week,
        'preferred_training_days': plan.preferred_training_days,
        'athlete_id': plan.athlete_id,
        'created_at': plan.created_at,
        'is_active': plan.is_active,
        'weeks': []
    }
    
    for week in plan.weeks:
        week_dict = {
            'week_number': week.week_number,
            'start_date': week.start_date.isoformat(),
            'end_date': week.end_date.isoformat(),
            'phase': week.phase.value,
            'week_type': week.week_type.value,
            'target_volume_km': week.target_volume_km,
            'target_duration_minutes': week.target_duration_minutes,
            'target_elevation_gain_m': week.target_elevation_gain_m,
            'focus': week.focus,
            'key_session_id': week.key_session_id,
            'notes': week.notes,
            'sessions': []
        }
        
        for session in week.sessions:
            # Sérialiser la structure (liste de PaceZone)
            structure_serialized = []
            for zone in session.structure:
                zone_dict = {
                    'description': zone.description,
                    'duration_minutes': zone.duration_minutes,
                    'distance_km': zone.distance_km,
                    'pace_min_per_km': zone.pace_min_per_km,
                    'pace_max_per_km': zone.pace_max_per_km,
                    'hr_zone': zone.hr_zone,
                    'repetitions': zone.repetitions,
                    'recovery_minutes': zone.recovery_minutes
                }
                structure_serialized.append(zone_dict)
            
            session_dict = {
                'id': session.id,
                'week_number': session.week_number,
                'day_of_week': session.day_of_week,
                'session_number': session.session_number,
                'session_type': session.session_type.value,
                'intensity': session.intensity.value,
                'title': session.title,
                'description': session.description,
                'duration_minutes': session.duration_minutes,
                'distance_km': session.distance_km,
                'structure': structure_serialized,
                'scheduled_date': session.scheduled_date.isoformat() if session.scheduled_date else None,
                'scheduled_time': session.scheduled_time,
                'status': session.status.value,
                'adaptation_reason': session.adaptation_reason,
                'original_session_id': session.original_session_id,
                'is_key_session': session.is_key_session,
                'can_be_postponed': session.can_be_postponed,
                'can_be_replaced': session.can_be_replaced,
                'completed_at': session.completed_at.isoformat() if session.completed_at else None,
                'actual_duration_minutes': session.actual_duration_minutes,
                'actual_distance_km': session.actual_distance_km,
                'average_pace': session.average_pace,
                'average_hr': session.average_hr,
                'max_hr': session.max_hr,
                'rpe': session.rpe,
                'feeling': session.feeling,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None
            }
            week_dict['sessions'].append(session_dict)
        
        plan_dict['weeks'].append(week_dict)
    
    # Sauvegarder
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(plan_dict, f, indent=2, ensure_ascii=False)


def load_plan_from_json(filepath: str = "data/training_plan.json") -> Optional[TrainingPlan]:
    """
    Charge le plan d'entraînement depuis un fichier JSON.
    
    Args:
        filepath: Chemin du fichier JSON
        
    Returns:
        Plan d'entraînement ou None si le fichier n'existe pas
    """
    path = Path(filepath)
    if not path.exists():
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            plan_dict = json.load(f)
        
        # Reconstruire le plan
        weeks = []
        for week_dict in plan_dict['weeks']:
            sessions = []
            for session_dict in week_dict['sessions']:
                # Reconstruire la structure (liste de PaceZone)
                structure = []
                for zone_dict in session_dict.get('structure', []):
                    zone = PaceZone(
                        description=zone_dict['description'],
                        duration_minutes=zone_dict.get('duration_minutes'),
                        distance_km=zone_dict.get('distance_km'),
                        pace_min_per_km=zone_dict['pace_min_per_km'],
                        pace_max_per_km=zone_dict.get('pace_max_per_km'),
                        hr_zone=zone_dict.get('hr_zone'),
                        repetitions=zone_dict.get('repetitions', 1),
                        recovery_minutes=zone_dict.get('recovery_minutes')
                    )
                    structure.append(zone)
                
                # Parser les dates si présentes
                from datetime import datetime
                completed_at = None
                if session_dict.get('completed_at'):
                    completed_at = datetime.fromisoformat(session_dict['completed_at'])
                
                created_at = datetime.now()
                if session_dict.get('created_at'):
                    created_at = datetime.fromisoformat(session_dict['created_at'])
                
                updated_at = datetime.now()
                if session_dict.get('updated_at'):
                    updated_at = datetime.fromisoformat(session_dict['updated_at'])
                
                session = TrainingSession(
                    id=session_dict['id'],
                    week_number=session_dict['week_number'],
                    day_of_week=session_dict['day_of_week'],
                    session_number=session_dict['session_number'],
                    session_type=SessionType(session_dict['session_type']),
                    intensity=SessionIntensity(session_dict['intensity']),
                    title=session_dict['title'],
                    description=session_dict['description'],
                    duration_minutes=session_dict['duration_minutes'],
                    distance_km=session_dict.get('distance_km'),
                    structure=structure,
                    scheduled_date=date.fromisoformat(session_dict['scheduled_date']) if session_dict.get('scheduled_date') else None,
                    scheduled_time=session_dict.get('scheduled_time'),
                    status=SessionStatus(session_dict.get('status', 'Planifiée')),
                    adaptation_reason=session_dict.get('adaptation_reason'),
                    original_session_id=session_dict.get('original_session_id'),
                    is_key_session=session_dict.get('is_key_session', False),
                    can_be_postponed=session_dict.get('can_be_postponed', True),
                    can_be_replaced=session_dict.get('can_be_replaced', True),
                    completed_at=completed_at,
                    actual_duration_minutes=session_dict.get('actual_duration_minutes'),
                    actual_distance_km=session_dict.get('actual_distance_km'),
                    average_pace=session_dict.get('average_pace'),
                    average_hr=session_dict.get('average_hr'),
                    max_hr=session_dict.get('max_hr'),
                    rpe=session_dict.get('rpe'),
                    feeling=session_dict.get('feeling'),
                    created_at=created_at,
                    updated_at=updated_at
                )
                sessions.append(session)
            
            week = TrainingWeek(
                week_number=week_dict['week_number'],
                start_date=date.fromisoformat(week_dict['start_date']),
                end_date=date.fromisoformat(week_dict['end_date']),
                phase=TrainingPhase(week_dict['phase']),
                week_type=WeekType(week_dict.get('week_type', 'Normale')),
                sessions=sessions,
                target_volume_km=week_dict.get('target_volume_km'),
                target_duration_minutes=week_dict.get('target_duration_minutes'),
                target_elevation_gain_m=week_dict.get('target_elevation_gain_m'),
                focus=week_dict.get('focus'),
                key_session_id=week_dict.get('key_session_id'),
                notes=week_dict.get('notes')
            )
            weeks.append(week)
        
        plan = TrainingPlan(
            id=plan_dict['id'],
            name=plan_dict['name'],
            description=plan_dict['description'],
            goal_distance=plan_dict['goal_distance'],
            goal_time=plan_dict['goal_time'],
            target_pace_per_km=plan_dict['target_pace_per_km'],
            start_date=date.fromisoformat(plan_dict['start_date']),
            end_date=date.fromisoformat(plan_dict['end_date']),
            duration_weeks=plan_dict['duration_weeks'],
            weeks=weeks,
            sessions_per_week=plan_dict.get('sessions_per_week', 4),
            preferred_training_days=plan_dict.get('preferred_training_days', [2, 4, 6, 7]),
            athlete_id=plan_dict['athlete_id'],
            created_at=plan_dict.get('created_at', str(date.today())),
            is_active=plan_dict.get('is_active', True)
        )
        
        return plan
    
    except Exception as e:
        print(f"Erreur lors du chargement du plan : {e}")
        return None


def get_or_create_plan(generator_func, filepath: str = "data/training_plan.json", force_new: bool = False, **kwargs) -> TrainingPlan:
    """
    Charge le plan depuis le fichier JSON ou en génère un nouveau.
    
    Args:
        generator_func: Fonction pour générer un nouveau plan
        filepath: Chemin du fichier JSON
        force_new: Si True, génère un nouveau plan même si un fichier existe
        **kwargs: Arguments à passer à generator_func
        
    Returns:
        Plan d'entraînement
    """
    if not force_new:
        plan = load_plan_from_json(filepath)
        if plan:
            return plan
    
    # Générer nouveau plan
    plan = generator_func(**kwargs)
    save_plan_to_json(plan, filepath)
    
    return plan
