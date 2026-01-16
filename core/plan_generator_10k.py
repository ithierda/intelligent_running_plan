"""
Générateur de plan d'entraînement pour 10km
"""
from datetime import date, timedelta
from models import (
    TrainingPlan, TrainingWeek, TrainingSession,
    TrainingPhase, WeekType, SessionType, SessionIntensity, PaceZone
)
from models.athlete_profile import AthleteProfile
from utils.pace_calculator import calculate_training_paces_from_vma, estimate_race_time
from typing import Optional


class Plan10kmGenerator:
    """
    Génère un plan d'entraînement pour 10km (6-12 semaines)
    
    Objectifs de temps supportés:
    - Sub 35min (3:30/km) - VMA ~20 km/h
    - Sub 40min (4:00/km) - VMA ~17 km/h
    - Sub 45min (4:30/km) - VMA ~15 km/h
    - Sub 50min (5:00/km) - VMA ~13.5 km/h
    """
    
    def __init__(
        self,
        athlete_id: str,
        start_date: date,
        race_date: date,
        target_time_minutes: int = 40,
        sessions_per_week: int = 4,
        preferred_days: list[int] = None,
        athlete_profile: Optional[AthleteProfile] = None
    ):
        self.athlete_id = athlete_id
        self.start_date = start_date
        self.race_date = race_date
        self.target_time_minutes = target_time_minutes
        self.sessions_per_week = sessions_per_week
        self.preferred_days = preferred_days or [2, 4, 6, 7]
        self.athlete_profile = athlete_profile
        
        # Calculer durée
        self.duration_weeks = (race_date - start_date).days // 7
        
        # Calculer l'allure cible en min/km si objectif fourni
        target_pace_min_per_km = None
        if target_time_minutes:
            target_pace_min_per_km = target_time_minutes / 10  # 10km
        
        # Allures selon objectif (ou VMA si profil disponible)
        if athlete_profile and athlete_profile.vma_kmh:
            # Utiliser VMA pour calculer toutes les allures
            self.paces_raw = calculate_training_paces_from_vma(
                athlete_profile.vma_kmh,
                fc_max=athlete_profile.max_heart_rate,
                fc_repos=athlete_profile.resting_heart_rate,
                level=athlete_profile.training_level,
                target_pace_min_per_km=target_pace_min_per_km,
                distance_km=10
            )
            self.using_vma = True
        elif target_time_minutes:
            # Calculer depuis l'objectif de temps SANS VMA
            from utils.pace_calculator import calculate_training_paces_from_target
            self.paces_raw = calculate_training_paces_from_target(target_time_minutes, 10)
            self.using_vma = True  # Même format de sortie
        else:
            # Ni VMA ni objectif : utiliser valeurs par défaut
            self.paces_raw = self._calculate_paces()
            self.using_vma = False
    
    def get_pace(self, zone: str, pace_type: str = 'target') -> str:
        """
        Récupère une allure depuis le dictionnaire de paces.
        Gère à la fois le format VMA (dict avec min/max/target) et le format simple (string).
        
        Args:
            zone: Zone d'allure ('easy', 'tempo', 'threshold', 'interval', 'race')
            pace_type: Type d'allure ('min', 'max', 'target')
        
        Returns:
            String au format "M:SS"
        """
        # Mapping des zones pour compatibilité VMA
        zone_mapping = {
            'race': '10k_race',  # Pour 10km, race = 10k_race (92-95% VMA)
            # 'easy' reste 'easy' (70-75% VMA) - PAS endurance !
            # 'interval' correspond à 10k_race pour les fractions
        }
        
        # Appliquer le mapping si nécessaire
        actual_zone = zone_mapping.get(zone, zone)
        
        if self.using_vma:
            # Format VMA: {'zone': {'min': 'M:SS', 'max': 'M:SS', 'target': 'M:SS'}}
            if actual_zone in self.paces_raw:
                zone_data = self.paces_raw[actual_zone]
                if isinstance(zone_data, dict):
                    return zone_data.get(pace_type, zone_data.get('target', '5:00'))
                return zone_data
            # Fallback pour zones non trouvées
            if zone == 'interval':
                # Intervalles = légèrement plus rapide que 10k race
                return self.paces_raw.get('10k_race', {}).get('max', '4:00')
            return self.paces_raw.get('easy', {}).get('target', '5:00')
        else:
            # Format simple: {'zone': 'M:SS'}
            return self.paces_raw.get(zone, '5:00')
    
    def _calculate_paces(self) -> dict:
        """Calcule les allures d'entraînement selon l'objectif"""
        target_pace_sec = (self.target_time_minutes * 60) / 10  # secondes/km
        target_pace_min = int(target_pace_sec // 60)
        target_pace_sec_rem = int(target_pace_sec % 60)
        target_pace = f"{target_pace_min}:{target_pace_sec_rem:02d}"
        
        # Zones d'entraînement (en sec/km)
        easy_pace_sec = target_pace_sec + 60  # +1min/km
        tempo_pace_sec = target_pace_sec + 20  # +20sec/km
        threshold_pace_sec = target_pace_sec + 10  # +10sec/km
        interval_pace_sec = target_pace_sec - 5  # -5sec/km (plus rapide)
        
        def sec_to_pace(sec):
            m = int(sec // 60)
            s = int(sec % 60)
            return f"{m}:{s:02d}"
        
        return {
            'easy': sec_to_pace(easy_pace_sec),
            'tempo': sec_to_pace(tempo_pace_sec),
            'threshold': sec_to_pace(threshold_pace_sec),
            'interval': sec_to_pace(interval_pace_sec),
            'race': target_pace
        }
    
    def generate_plan(self) -> TrainingPlan:
        """Génère le plan complet"""
        # Calculer l'allure cible depuis l'objectif de temps (pas VMA)
        target_pace_sec = (self.target_time_minutes * 60) / 10  # secondes/km
        target_pace_min = int(target_pace_sec // 60)
        target_pace_sec_rem = int(target_pace_sec % 60)
        target_pace = f"{target_pace_min}:{target_pace_sec_rem:02d}"
        
        plan = TrainingPlan(
            id=f"10k_{self.target_time_minutes}min_{self.athlete_id}_{self.start_date.isoformat()}",
            name=f"10km Sub {self.target_time_minutes}min",
            description=f"Plan structuré pour courir 10km en moins de {self.target_time_minutes} minutes",
            goal_distance="10km",
            goal_time=f"{self.target_time_minutes}:00",
            target_pace_per_km=target_pace,  # Utiliser l'objectif réel, pas VMA
            start_date=self.start_date,
            end_date=self.race_date,
            duration_weeks=self.duration_weeks,
            sessions_per_week=self.sessions_per_week,
            preferred_training_days=self.preferred_days,
            athlete_id=self.athlete_id
        )
        
        # Définir les phases
        phases = self._calculate_phases()
        
        # Générer les semaines
        for week_num in range(1, self.duration_weeks + 1):
            phase = self._get_phase_for_week(week_num, phases)
            week = self._generate_week(week_num, phase)
            plan.add_week(week)
        
        return plan
    
    def _calculate_phases(self) -> dict:
        """Calcule la répartition des phases pour 10km"""
        total = self.duration_weeks
        
        if total <= 6:
            return {
                'base': 2,
                'build': 3,
                'peak': 1,
                'taper': 0
            }
        elif total <= 9:
            return {
                'base': 3,
                'build': 4,
                'peak': 1,
                'taper': 1
            }
        else:  # 10-12 semaines
            return {
                'base': 4,
                'build': 5,
                'peak': 2,
                'taper': 1
            }
    
    def _get_phase_for_week(self, week_num: int, phases: dict) -> TrainingPhase:
        """Détermine la phase pour une semaine donnée"""
        if week_num <= phases['base']:
            return TrainingPhase.BASE
        elif week_num <= phases['base'] + phases['build']:
            return TrainingPhase.BUILD
        elif week_num <= phases['base'] + phases['build'] + phases['peak']:
            return TrainingPhase.PEAK
        else:
            return TrainingPhase.TAPER
    
    def _generate_week(self, week_num: int, phase: TrainingPhase) -> TrainingWeek:
        """Génère une semaine d'entraînement"""
        week_start = self.start_date + timedelta(weeks=week_num - 1)
        week_end = week_start + timedelta(days=6)
        
        week = TrainingWeek(
            week_number=week_num,
            start_date=week_start,
            end_date=week_end,
            phase=phase,
            week_type=WeekType.PEAK if phase == TrainingPhase.PEAK else WeekType.NORMAL
        )
        
        # Générer séances selon la phase
        sessions = self._create_sessions_for_phase(week_num, phase)
        
        for i, session in enumerate(sessions, 1):
            if i <= len(self.preferred_days):
                session.day_of_week = self.preferred_days[i - 1]
                session.scheduled_date = week_start + timedelta(days=session.day_of_week - 1)
                session.week_number = week_num
                session.session_number = i
                week.sessions.append(session)
        
        return week
    
    def _create_sessions_for_phase(self, week_num: int, phase: TrainingPhase) -> list[TrainingSession]:
        """Crée les séances selon la phase"""
        sessions = []
        
        if phase == TrainingPhase.BASE:
            # Phase de base : volume et endurance
            sessions.append(self._create_easy_run(40, "Footing facile"))
            sessions.append(self._create_tempo_session(week_num))
            sessions.append(self._create_easy_run(35, "Récupération"))
            if self.sessions_per_week >= 4:
                sessions.append(self._create_long_run(week_num))
        
        elif phase == TrainingPhase.BUILD:
            # Phase de développement : intervalles + seuil
            sessions.append(self._create_easy_run(40, "Footing facile"))
            sessions.append(self._create_interval_session(week_num))
            sessions.append(self._create_easy_run(35, "Récupération"))
            if self.sessions_per_week >= 4:
                sessions.append(self._create_threshold_session(week_num))
            if self.sessions_per_week >= 5:
                sessions.append(self._create_long_run(week_num))
        
        elif phase == TrainingPhase.PEAK:
            # Phase pic : spécifique 10km
            sessions.append(self._create_easy_run(35, "Footing léger"))
            sessions.append(self._create_race_pace_session(week_num))
            sessions.append(self._create_easy_run(30, "Récupération"))
            if self.sessions_per_week >= 4:
                sessions.append(self._create_interval_session(week_num, short=True))
        
        else:  # TAPER
            # Affûtage
            sessions.append(self._create_easy_run(25, "Footing très léger"))
            sessions.append(self._create_sharpening_session())
            sessions.append(self._create_easy_run(20, "Activation pré-course"))
        
        return sessions[:self.sessions_per_week]
    
    def _create_easy_run(self, duration: int, title: str) -> TrainingSession:
        """Crée un footing facile"""
        # Calculer la distance correctement depuis l'allure
        pace_str = self.get_pace('easy')
        pace_parts = pace_str.split(':')
        pace_min_per_km = int(pace_parts[0]) + int(pace_parts[1]) / 60.0
        distance = round(duration / pace_min_per_km, 1)
        
        return TrainingSession(
            id=f"easy_{duration}min",
            title=title,
            description=f"Course facile de {duration} minutes à allure confortable",
            session_type=SessionType.ENDURANCE,
            intensity=SessionIntensity.EASY,
            duration_minutes=duration,
            distance_km=distance,
            structure=[
                PaceZone(
                    description="Footing facile",
                    duration_minutes=duration,
                    pace_min_per_km=self.get_pace('easy'),
                    hr_zone="65-75% FCmax"
                )
            ],
            week_number=1,
            day_of_week=1,
            session_number=1
        )
    
    def _create_long_run(self, week_num: int) -> TrainingSession:
        """Crée une sortie longue"""
        duration = 50 + (week_num - 1) * 5  # Progression
        duration = min(duration, 90)  # Max 90min
        
        # Calculer la distance correctement depuis l'allure
        pace_str = self.get_pace('easy')
        pace_parts = pace_str.split(':')
        pace_min_per_km = int(pace_parts[0]) + int(pace_parts[1]) / 60.0
        distance = round(duration / pace_min_per_km, 1)
        
        return TrainingSession(
            id=f"long_{week_num}",
            title=f"Sortie longue {duration}min",
            description=f"Sortie longue en endurance fondamentale",
            session_type=SessionType.LONG_RUN,
            intensity=SessionIntensity.EASY,
            duration_minutes=duration,
            distance_km=distance,
            structure=[
                PaceZone(
                    description="Endurance",
                    duration_minutes=duration,
                    pace_min_per_km=self.get_pace('easy'),
                    hr_zone="70-75% FCmax"
                )
            ],
            is_key_session=True,
            week_number=1,
            day_of_week=1,
            session_number=1
        )
    
    def _create_tempo_session(self, week_num: int) -> TrainingSession:
        """Crée une séance tempo"""
        duration = 20 + (week_num - 1) * 2  # Progression
        duration = min(duration, 35)
        
        return TrainingSession(
            id=f"tempo_{week_num}",
            title=f"Tempo {duration}min",
            description=f"Allure soutenue pendant {duration} minutes",
            session_type=SessionType.TEMPO,
            intensity=SessionIntensity.MODERATE,
            duration_minutes=55,
            distance_km=9.0,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=15, pace_min_per_km=self.get_pace('easy')),
                PaceZone(description="Tempo", duration_minutes=duration, pace_min_per_km=self.get_pace('tempo'), hr_zone="80-85% FCmax"),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('easy'))
            ],
            is_key_session=True,
            week_number=1,
            day_of_week=1,
            session_number=1
        )
    
    def _create_interval_session(self, week_num: int, short: bool = False) -> TrainingSession:
        """Crée une séance d'intervalles"""
        if short:
            # Intervalles courts pour peak
            reps = 10
            duration = 1
            recovery = 1
            title = "10x1min"
        else:
            # Intervalles 1000m
            reps = 5 + min((week_num - 3) // 2, 3)  # 5 à 8 reps
            duration = 3
            recovery = 2
            title = f"{reps}x1000m"
        
        return TrainingSession(
            id=f"intervals_{week_num}",
            title=title,
            description=f"{reps} répétitions à allure intervalle",
            session_type=SessionType.INTERVALS,
            intensity=SessionIntensity.HARD,
            duration_minutes=60,
            distance_km=10.0,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=20, pace_min_per_km=self.get_pace('easy')),
                PaceZone(
                    description=f"Intervalle {duration}min",
                    duration_minutes=duration,
                    pace_min_per_km=self.get_pace('interval'),
                    hr_zone="90-95% FCmax",
                    repetitions=reps,
                    recovery_minutes=recovery
                ),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('easy'))
            ],
            is_key_session=True,
            week_number=1,
            day_of_week=1,
            session_number=1
        )
    
    def _create_threshold_session(self, week_num: int) -> TrainingSession:
        """Crée une séance au seuil"""
        reps = 2 + min((week_num - 3) // 2, 2)  # 2 à 4 reps
        duration = 8
        
        return TrainingSession(
            id=f"threshold_{week_num}",
            title=f"{reps}x{duration}min au seuil",
            description=f"{reps} fractions de {duration}min à allure seuil",
            session_type=SessionType.THRESHOLD,
            intensity=SessionIntensity.HARD,
            duration_minutes=60,
            distance_km=10.5,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=20, pace_min_per_km=self.get_pace('easy')),
                PaceZone(
                    description=f"Seuil {duration}min",
                    duration_minutes=duration,
                    pace_min_per_km=self.get_pace('threshold'),
                    hr_zone="85-90% FCmax",
                    repetitions=reps,
                    recovery_minutes=3
                ),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('easy'))
            ],
            is_key_session=True,
            week_number=1,
            day_of_week=1,
            session_number=1
        )
    
    def _create_race_pace_session(self, week_num: int) -> TrainingSession:
        """Crée une séance à allure course"""
        return TrainingSession(
            id=f"race_pace_{week_num}",
            title="6km allure course",
            description="6km à l'allure cible de la course",
            session_type=SessionType.TEMPO,
            intensity=SessionIntensity.HARD,
            duration_minutes=55,
            distance_km=10.0,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=20, pace_min_per_km=self.get_pace('easy')),
                PaceZone(description="6km allure course", distance_km=6.0, pace_min_per_km=self.get_pace('race'), hr_zone="90% FCmax"),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('easy'))
            ],
            is_key_session=True,
            week_number=1,
            day_of_week=1,
            session_number=1
        )
    
    def _create_sharpening_session(self) -> TrainingSession:
        """Séance d'affûtage pré-course"""
        return TrainingSession(
            id="sharpening",
            title="Affûtage 6x800m",
            description="Intervalles moyens pour garder la vitesse",
            session_type=SessionType.INTERVALS,
            intensity=SessionIntensity.MODERATE,
            duration_minutes=45,
            distance_km=7.0,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=20, pace_min_per_km=self.get_pace('easy')),
                PaceZone(
                    description="800m vif",
                    distance_km=0.8,
                    pace_min_per_km=self.get_pace('interval'),
                    repetitions=6,
                    recovery_minutes=2
                ),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('easy'))
            ],
            week_number=1,
            day_of_week=1,
            session_number=1
        )


def generate_10k_plan(
    athlete_id: str,
    start_date: date,
    race_date: date,
    target_time_minutes: int = 40,
    sessions_per_week: int = 4,
    preferred_days: list[int] = None,
    athlete_profile: Optional[AthleteProfile] = None
) -> TrainingPlan:
    """
    Fonction helper pour générer un plan 10km
    
    Args:
        athlete_id: ID de l'athlète
        start_date: Date de début du plan
        race_date: Date de la course
        target_time_minutes: Objectif en minutes (35, 40, 45, 50)
        sessions_per_week: Nombre de séances par semaine
        preferred_days: Jours préférés (1=lundi, 7=dimanche)
        athlete_profile: Profil de l'athlète (pour allures personnalisées)
    
    Returns:
        TrainingPlan complet
    """
    generator = Plan10kmGenerator(
        athlete_id=athlete_id,
        start_date=start_date,
        race_date=race_date,
        target_time_minutes=target_time_minutes,
        sessions_per_week=sessions_per_week,
        preferred_days=preferred_days,
        athlete_profile=athlete_profile
    )
    return generator.generate_plan()
