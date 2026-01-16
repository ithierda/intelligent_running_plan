"""
Générateur de plan d'entraînement pour semi-marathon sub 1:45
"""
from datetime import date, timedelta
from models import (
    TrainingPlan, TrainingWeek, TrainingSession,
    TrainingPhase, WeekType, SessionType, SessionIntensity, PaceZone
)
from models.athlete_profile import AthleteProfile
from config.settings import SEMI_145_PACES
from utils.pace_calculator import calculate_training_paces_from_vma, calculate_heart_rate_zones, estimate_race_time
from typing import Optional



class SemiMarathonPlanGenerator:
    """
    Génère un plan d'entraînement structuré pour semi-marathon sub 1:45
    
    Prérequis:
    - VMA ~17 km/h
    - Capable de courir 10km en ~50min
    - 4 séances/semaine minimum
    """
    
    def __init__(
        self,
        athlete_id: str,
        start_date: date,
        race_date: date,
        sessions_per_week: int = 4,
        preferred_days: list[int] = None,
        athlete_profile: Optional[AthleteProfile] = None,
        target_time_minutes: Optional[int] = None
    ):
        self.athlete_id = athlete_id
        self.start_date = self._get_monday(start_date)
        self.race_date = race_date
        self.sessions_per_week = sessions_per_week
        self.preferred_days = preferred_days or [2, 4, 6, 7]  # Mar, Jeu, Sam, Dim
        self.athlete_profile = athlete_profile
        self.target_time_minutes = target_time_minutes  # Objectif choisi par l'utilisateur
        
        # Calculer l'allure cible en min/km si objectif fourni
        target_pace_min_per_km = None
        if target_time_minutes:
            target_pace_min_per_km = target_time_minutes / 21.1  # Semi-marathon
        
        # Calculer les allures personnalisées si profil disponible
        if athlete_profile and athlete_profile.vma_kmh:
            self.paces_raw = calculate_training_paces_from_vma(
                athlete_profile.vma_kmh,
                fc_max=athlete_profile.max_heart_rate,
                fc_repos=athlete_profile.resting_heart_rate,
                level=athlete_profile.training_level,
                target_pace_min_per_km=target_pace_min_per_km,
                distance_km=21.1
            )
            self.using_vma = True
        elif target_time_minutes:
            # Calculer depuis l'objectif SANS VMA
            from utils.pace_calculator import calculate_training_paces_from_target
            self.paces_raw = calculate_training_paces_from_target(target_time_minutes, 21.1)
            self.using_vma = True  # Même format de sortie
        else:
            # Utiliser les allures par défaut (VMA 17 km/h)
            self.paces_raw = SEMI_145_PACES
            self.using_vma = False
        
        # Calculer les zones FC personnalisées si profil disponible
        if athlete_profile:
            fc_max = athlete_profile.get_max_heart_rate()
            fc_repos = athlete_profile.resting_heart_rate
            self.hr_zones = calculate_heart_rate_zones(fc_max, fc_repos)
        else:
            self.hr_zones = None
        
        # Calculer le nombre de semaines
        delta = race_date - self.start_date
        self.duration_weeks = delta.days // 7
        
        if self.duration_weeks < 8:
            raise ValueError("Le plan doit durer au moins 8 semaines")
        if self.duration_weeks > 16:
            print(f"⚠️ Attention: plan de {self.duration_weeks} semaines (recommandé: 12-14)")
    
    def get_pace(self, zone: str, pace_type: str = 'target') -> str:
        """
        Récupère une allure selon la zone
        
        Args:
            zone: Nom de la zone (endurance, tempo, threshold, vma, semi_race, etc.)
            pace_type: 'min', 'max' ou 'target' (uniquement si VMA utilisée)
        
        Returns:
            Allure formatée "M:SS"
        """
        if self.using_vma:
            # Avec VMA, on a des dictionnaires {min, max, target}
            if zone in self.paces_raw:
                return self.paces_raw[zone].get(pace_type, self.paces_raw[zone].get('target', '5:00'))
            # Fallback pour zones manquantes
            return '5:00'
        else:
            # Sans VMA, on a juste des strings
            # Mapper les noms de zones si nécessaire
            zone_mapping = {
                'semi_race': 'threshold',
                '10k_race': 'threshold',
                '5k_race': 'intervals',
                'easy': 'endurance',
                'recovery': 'recovery'
            }
            actual_zone = zone_mapping.get(zone, zone)
            return self.paces_raw.get(actual_zone, self.paces_raw.get('endurance', '5:00'))
    
    def _get_monday(self, d: date) -> date:
        """Retourne le lundi de la semaine"""
        while d.weekday() != 0:  # 0 = lundi
            d -= timedelta(days=1)
        return d
    
    def generate_plan(self) -> TrainingPlan:
        """Génère le plan complet"""
        
        # Calculer l'objectif et l'allure cible
        # Priorité : 1) target_time_minutes (choix utilisateur), 2) VMA, 3) défaut
        
        if self.target_time_minutes:
            # L'utilisateur a choisi un objectif spécifique
            hours = self.target_time_minutes // 60
            mins = self.target_time_minutes % 60
            goal_time = f"{hours}:{mins:02d}:00"
            
            # Calculer allure cible (min/km)
            target_pace_sec = (self.target_time_minutes * 60) / 21.1
            target_pace_min = int(target_pace_sec // 60)
            target_pace_sec_rem = int(target_pace_sec % 60)
            target_pace = f"{target_pace_min}:{target_pace_sec_rem:02d}"
            
            # Nom du plan basé sur l'objectif choisi
            if hours == 1 and mins == 30:
                plan_name = "Semi-Marathon Sub 1:30"
            elif hours == 1 and mins == 35:
                plan_name = "Semi-Marathon Sub 1:35"
            elif hours == 1 and mins == 40:
                plan_name = "Semi-Marathon Sub 1:40"
            elif hours == 1 and mins == 45:
                plan_name = "Semi-Marathon Sub 1:45"
            elif hours == 1 and mins == 50:
                plan_name = "Semi-Marathon Sub 1:50"
            elif hours == 2:
                plan_name = "Semi-Marathon Sub 2:00"
            else:
                plan_name = f"Semi-Marathon Sub {hours}:{mins:02d}"
                
            # Ajouter info VMA si disponible
            if self.athlete_profile and self.athlete_profile.vma_kmh:
                est_minutes, est_time_str = estimate_race_time(21.1, self.athlete_profile.vma_kmh)
                plan_name += f" (VMA suggère: {est_time_str})"
                
        elif self.athlete_profile and self.athlete_profile.vma_kmh:
            # Pas d'objectif choisi, utiliser la VMA
            est_minutes, est_time_str = estimate_race_time(21.1, self.athlete_profile.vma_kmh)
            hours = est_minutes // 60
            mins = est_minutes % 60
            goal_time = f"{hours}:{mins:02d}:00"
            
            # Calculer allure cible (min/km)
            target_pace_sec = (est_minutes * 60) / 21.1
            target_pace_min = int(target_pace_sec // 60)
            target_pace_sec_rem = int(target_pace_sec % 60)
            target_pace = f"{target_pace_min}:{target_pace_sec_rem:02d}"
            
            # Nom du plan basé sur l'objectif VMA
            if hours == 1 and mins < 30:
                plan_name = f"Semi-Marathon Sub 1:30 (objectif: {est_time_str})"
            elif hours == 1 and mins < 45:
                plan_name = f"Semi-Marathon Sub 1:45 (objectif: {est_time_str})"
            elif hours == 2:
                plan_name = f"Semi-Marathon Sub 2:00 (objectif: {est_time_str})"
            else:
                plan_name = f"Semi-Marathon (objectif: {est_time_str})"
        else:
            # Valeurs par défaut (Sub 1:45)
            goal_time = "1:45:00"
            target_pace = "4:58"
            plan_name = "Semi-Marathon Sub 1:45"
        
        plan = TrainingPlan(
            id=f"semi_{self.athlete_id}_{self.start_date.isoformat()}",
            name=plan_name,
            description=f"Plan structuré en 3 phases pour réussir un semi-marathon (objectif: {goal_time})",
            goal_distance="Semi-marathon",
            goal_time=goal_time,
            target_pace_per_km=target_pace,
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
        """Calcule la répartition des phases"""
        total = self.duration_weeks
        
        if total <= 10:
            # Plan court
            return {
                'base': (1, 3),
                'build': (4, 8),
                'taper': (9, total)
            }
        elif total <= 12:
            # Plan standard
            return {
                'base': (1, 4),
                'build': (5, 10),
                'taper': (11, total)
            }
        else:
            # Plan long
            base_weeks = int(total * 0.3)
            build_weeks = int(total * 0.6)
            return {
                'base': (1, base_weeks),
                'build': (base_weeks + 1, base_weeks + build_weeks),
                'taper': (base_weeks + build_weeks + 1, total)
            }
    
    def _get_phase_for_week(self, week_num: int, phases: dict) -> TrainingPhase:
        """Détermine la phase d'une semaine"""
        if phases['base'][0] <= week_num <= phases['base'][1]:
            return TrainingPhase.BASE
        elif phases['build'][0] <= week_num <= phases['build'][1]:
            return TrainingPhase.BUILD
        else:
            return TrainingPhase.TAPER
    
    def _generate_week(self, week_number: int, phase: TrainingPhase) -> TrainingWeek:
        """Génère une semaine d'entraînement"""
        week_start = self.start_date + timedelta(weeks=week_number - 1)
        week_end = week_start + timedelta(days=6)
        
        # Semaine de récupération toutes les 3-4 semaines
        is_recovery_week = (week_number % 4 == 0) and week_number < self.duration_weeks - 2
        week_type = WeekType.RECOVERY if is_recovery_week else WeekType.NORMAL
        
        # Dernière semaine = course
        if week_number == self.duration_weeks:
            week_type = WeekType.RACE
        
        week = TrainingWeek(
            week_number=week_number,
            start_date=week_start,
            end_date=week_end,
            phase=phase,
            week_type=week_type
        )
        
        # Générer les séances selon la phase
        if phase == TrainingPhase.BASE:
            sessions = self._generate_base_sessions(week_number, is_recovery_week)
        elif phase == TrainingPhase.BUILD:
            sessions = self._generate_build_sessions(week_number, is_recovery_week)
        else:  # TAPER
            sessions = self._generate_taper_sessions(week_number)
        
        # Assigner les jours et ajouter à la semaine
        for i, session in enumerate(sessions):
            day = self.preferred_days[i % len(self.preferred_days)]
            session.day_of_week = day
            session.session_number = i + 1
            week.add_session(session)
        
        return week
    
    def _generate_base_sessions(self, week_num: int, is_recovery: bool) -> list[TrainingSession]:
        """Génère les séances de la phase de base"""
        sessions = []
        factor = 0.75 if is_recovery else 1.0
        
        # Séance 1: Endurance fondamentale
        sessions.append(TrainingSession(
            id=f"W{week_num}_S1",
            week_number=week_num,
            day_of_week=1,
            session_number=1,
            session_type=SessionType.ENDURANCE,
            intensity=SessionIntensity.EASY,
            title="Endurance fondamentale",
            description="Course facile à allure conversationnelle",
            duration_minutes=int(50 * factor),
            distance_km=8.0 * factor,
            structure=[
                PaceZone(
                    description="Endurance fondamentale",
                    duration_minutes=int(50 * factor),
                    pace_min_per_km=self.get_pace('endurance', 'target'),
                    pace_max_per_km="6:15",
                    hr_zone="75-80% FCmax"
                )
            ]
        ))
        
        # Séance 2: Fartlek ou tempo léger
        sessions.append(TrainingSession(
            id=f"W{week_num}_S2",
            week_number=week_num,
            day_of_week=2,
            session_number=2,
            session_type=SessionType.FARTLEK,
            intensity=SessionIntensity.MODERATE,
            title="Fartlek léger",
            description="Variations d'allure en nature",
            duration_minutes=int(45 * factor),
            distance_km=7.5 * factor,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=10, pace_min_per_km=self.get_pace('easy', 'target')),
                PaceZone(description="Fartlek (accélérations libres)", duration_minutes=int(25 * factor), 
                        pace_min_per_km=self.get_pace('tempo', 'target'), hr_zone="80-87% FCmax"),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('recovery', 'max'))
            ]
        ))
        
        # Séance 3: Endurance courte
        sessions.append(TrainingSession(
            id=f"W{week_num}_S3",
            week_number=week_num,
            day_of_week=3,
            session_number=3,
            session_type=SessionType.ENDURANCE,
            intensity=SessionIntensity.EASY,
            title="Endurance moyenne",
            description="Course facile de récupération",
            duration_minutes=int(40 * factor),
            distance_km=6.5 * factor,
            structure=[
                PaceZone(description="Endurance", duration_minutes=int(40 * factor),
                        pace_min_per_km=self.get_pace('endurance', 'target'), hr_zone="75-80% FCmax")
            ]
        ))
        
        # Séance 4: Sortie longue
        long_duration = min(60 + (week_num * 5), 90)  # Progression
        sessions.append(TrainingSession(
            id=f"W{week_num}_S4",
            week_number=week_num,
            day_of_week=4,
            session_number=4,
            session_type=SessionType.LONG_RUN,
            intensity=SessionIntensity.MODERATE,
            title=f"Sortie longue {int(long_duration * factor)}min",
            description="Sortie longue à allure confortable",
            duration_minutes=int(long_duration * factor),
            distance_km=round((long_duration / 6) * factor, 1),  # ~6min/km
            is_key_session=True,
            structure=[
                PaceZone(description="Endurance longue", duration_minutes=int(long_duration * factor),
                        pace_min_per_km=self.get_pace('endurance', 'min'), pace_max_per_km=self.get_pace('endurance', 'max'), hr_zone="75-82% FCmax")
            ]
        ))
        
        return sessions
    
    def _generate_build_sessions(self, week_num: int, is_recovery: bool) -> list[TrainingSession]:
        """Génère les séances de la phase de développement (intensif)"""
        sessions = []
        factor = 0.8 if is_recovery else 1.0
        
        # Séance 1: VMA ou intervalles
        sessions.append(TrainingSession(
            id=f"W{week_num}_S1",
            week_number=week_num,
            day_of_week=1,
            session_number=1,
            session_type=SessionType.INTERVALS,
            intensity=SessionIntensity.VERY_HARD,
            title="VMA courte",
            description="Intervalles courts à VMA",
            duration_minutes=int(55 * factor),
            distance_km=9.0 * factor,
            is_key_session=True,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=15, pace_min_per_km=self.get_pace('easy', 'target')),
                PaceZone(description="400m VMA", distance_km=0.4, pace_min_per_km=self.get_pace('vma', 'target'),
                        hr_zone="95-100% FCmax", repetitions=int(8 * factor), recovery_minutes=1.5),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('recovery', 'max'))
            ]
        ))
        
        # Séance 2: Seuil / Allure semi
        sessions.append(TrainingSession(
            id=f"W{week_num}_S2",
            week_number=week_num,
            day_of_week=2,
            session_number=2,
            session_type=SessionType.THRESHOLD,
            intensity=SessionIntensity.HARD,
            title="Seuil / Allure semi",
            description="Blocs à allure semi-marathon",
            duration_minutes=int(60 * factor),
            distance_km=12.0 * factor,
            is_key_session=True,
            structure=[
                PaceZone(description="Échauffement", duration_minutes=15, pace_min_per_km=self.get_pace('easy', 'target')),
                PaceZone(description="Bloc allure semi", duration_minutes=int(10 * factor),
                        pace_min_per_km=self.get_pace('semi_race', 'target'), pace_max_per_km=self.get_pace('semi_race', 'max'),
                        hr_zone="87-92% FCmax", repetitions=3, recovery_minutes=2),
                PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('recovery', 'max'))
            ]
        ))
        
        # Séance 3: Endurance active
        sessions.append(TrainingSession(
            id=f"W{week_num}_S3",
            week_number=week_num,
            day_of_week=3,
            session_number=3,
            session_type=SessionType.ENDURANCE,
            intensity=SessionIntensity.EASY,
            title="Récupération active",
            description="Endurance légère entre les séances intenses",
            duration_minutes=int(45 * factor),
            distance_km=7.5 * factor,
            structure=[
                PaceZone(description="Endurance facile", duration_minutes=int(45 * factor),
                        pace_min_per_km=self.get_pace('endurance', 'target'), hr_zone="75-80% FCmax")
            ]
        ))
        
        # Séance 4: Sortie longue avec finish
        long_duration = min(75 + (week_num * 3), 105)
        sessions.append(TrainingSession(
            id=f"W{week_num}_S4",
            week_number=week_num,
            day_of_week=4,
            session_number=4,
            session_type=SessionType.LONG_RUN,
            intensity=SessionIntensity.MODERATE,
            title=f"Sortie longue progressive {int(long_duration * factor)}min",
            description="Sortie longue avec finish plus rapide",
            duration_minutes=int(long_duration * factor),
            distance_km=round((long_duration / 5.8) * factor, 1),
            is_key_session=True,
            structure=[
                PaceZone(description="Endurance de base", duration_minutes=int((long_duration - 20) * factor),
                        pace_min_per_km=self.get_pace('endurance', 'target'), hr_zone="75-80% FCmax"),
                PaceZone(description="Finish allure semi", duration_minutes=int(20 * factor),
                        pace_min_per_km=self.get_pace('semi_race', 'target'), hr_zone="87-90% FCmax")
            ]
        ))
        
        return sessions
    
    def _generate_taper_sessions(self, week_num: int) -> list[TrainingSession]:
        """Génère les séances de la phase d'affûtage"""
        sessions = []
        weeks_to_race = self.duration_weeks - week_num + 1
        
        if weeks_to_race == 1:
            # Semaine de course: volume très réduit
            sessions.append(TrainingSession(
                id=f"W{week_num}_S1",
                week_number=week_num,
                day_of_week=1,
                session_number=1,
                session_type=SessionType.ENDURANCE,
                intensity=SessionIntensity.VERY_EASY,
                title="Décrassage léger",
                description="Course très facile pour rester actif",
                duration_minutes=30,
                distance_km=5.0,
                structure=[
                    PaceZone(description="Endurance très légère", duration_minutes=30,
                            pace_min_per_km=self.get_pace('recovery', 'max'), hr_zone="70-75% FCmax")
                ]
            ))
            
            sessions.append(TrainingSession(
                id=f"W{week_num}_S2",
                week_number=week_num,
                day_of_week=2,
                session_number=2,
                session_type=SessionType.INTERVALS,
                intensity=SessionIntensity.MODERATE,
                title="Rappel VMA court",
                description="Quelques accélérations pour garder jambes vives",
                duration_minutes=35,
                distance_km=5.5,
                structure=[
                    PaceZone(description="Échauffement", duration_minutes=15, pace_min_per_km=self.get_pace('easy', 'target')),
                    PaceZone(description="200m rapide", distance_km=0.2,
                            pace_min_per_km="3:20", repetitions=4, recovery_minutes=2),
                    PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('recovery', 'max'))
                ]
            ))
            
            # RACE DAY
            sessions.append(TrainingSession(
                id=f"W{week_num}_RACE",
                week_number=week_num,
                day_of_week=7,  # Dimanche généralement
                session_number=3,
                session_type=SessionType.RACE,
                intensity=SessionIntensity.VERY_HARD,
                title="🏁 SEMI-MARATHON - Objectif 1:45",
                description="Course cible ! Objectif: 4:58/km de moyenne. Bonne chance ! 🚀",
                duration_minutes=105,
                distance_km=21.1,
                is_key_session=True,
                can_be_postponed=False,
                can_be_replaced=False,
                structure=[
                    PaceZone(description="Km 1-5: Mise en route", distance_km=5.0,
                            pace_min_per_km=self.get_pace('endurance', 'max'), hr_zone="82-87% FCmax"),
                    PaceZone(description="Km 6-15: Rythme de croisière", distance_km=10.0,
                            pace_min_per_km=self.get_pace('semi_race', 'target'), hr_zone="87-92% FCmax"),
                    PaceZone(description="Km 16-21: Push final", distance_km=6.1,
                            pace_min_per_km=self.get_pace('semi_race', 'max'), hr_zone="90-95% FCmax")
                ]
            ))
            
        else:
            # 2-3 semaines avant: volume réduit, intensité maintenue
            reduction = 0.7 if weeks_to_race == 2 else 0.85
            
            sessions.append(TrainingSession(
                id=f"W{week_num}_S1",
                week_number=week_num,
                day_of_week=1,
                session_number=1,
                session_type=SessionType.INTERVALS,
                intensity=SessionIntensity.HARD,
                title="VMA réduite",
                description="Maintien qualité, volume réduit",
                duration_minutes=int(50 * reduction),
                distance_km=8.0 * reduction,
                is_key_session=True,
                structure=[
                    PaceZone(description="Échauffement", duration_minutes=15, pace_min_per_km=self.get_pace('easy', 'target')),
                    PaceZone(description="300m VMA", distance_km=0.3,
                            pace_min_per_km=self.get_pace('vma', 'target'),
                            repetitions=int(6 * reduction), recovery_minutes=1.5),
                    PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('recovery', 'max'))
                ]
            ))
            
            sessions.append(TrainingSession(
                id=f"W{week_num}_S2",
                week_number=week_num,
                day_of_week=2,
                session_number=2,
                session_type=SessionType.TEMPO,
                intensity=SessionIntensity.MODERATE,
                title="Allure spécifique",
                description="Blocs courts à allure cible",
                duration_minutes=int(55 * reduction),
                distance_km=10.0 * reduction,
                is_key_session=True,
                structure=[
                    PaceZone(description="Échauffement", duration_minutes=15, pace_min_per_km=self.get_pace('easy', 'target')),
                    PaceZone(description="Allure semi", duration_minutes=int(8 * reduction),
                            pace_min_per_km=self.get_pace('semi_race', 'target'),
                            repetitions=2, recovery_minutes=3),
                    PaceZone(description="Retour au calme", duration_minutes=10, pace_min_per_km=self.get_pace('recovery', 'max'))
                ]
            ))
            
            sessions.append(TrainingSession(
                id=f"W{week_num}_S3",
                week_number=week_num,
                day_of_week=3,
                session_number=3,
                session_type=SessionType.ENDURANCE,
                intensity=SessionIntensity.EASY,
                title="Endurance facile",
                description="Récupération active",
                duration_minutes=int(45 * reduction),
                distance_km=7.5 * reduction,
                structure=[
                    PaceZone(description="Endurance", duration_minutes=int(45 * reduction),
                            pace_min_per_km=self.get_pace('endurance', 'target'), hr_zone="75-80% FCmax")
                ]
            ))
            
            sessions.append(TrainingSession(
                id=f"W{week_num}_S4",
                week_number=week_num,
                day_of_week=4,
                session_number=4,
                session_type=SessionType.LONG_RUN,
                intensity=SessionIntensity.EASY,
                title=f"Sortie longue allégée",
                description="Sortie longue réduite pour affûtage",
                duration_minutes=int(65 * reduction),
                distance_km=11.0 * reduction,
                structure=[
                    PaceZone(description="Endurance confortable", duration_minutes=int(65 * reduction),
                            pace_min_per_km="6:00", hr_zone="75-82% FCmax")
                ]
            ))
        
        return sessions


# Fonction utilitaire
def generate_semi_145_plan(
    athlete_id: str,
    start_date: date,
    race_date: date,
    sessions_per_week: int = 4,
    preferred_days: list[int] = None,
    athlete_profile: Optional['AthleteProfile'] = None,
    target_time_minutes: Optional[int] = None
) -> TrainingPlan:
    """
    Fonction helper pour générer un plan semi-marathon
    
    Args:
        athlete_id: ID de l'athlète
        start_date: Date de début du plan
        race_date: Date de la course
        sessions_per_week: Nombre de séances par semaine (4 recommandé)
        preferred_days: Jours préférés (1=lundi, 7=dimanche)
        athlete_profile: Profil de l'athlète (pour allures personnalisées)
        target_time_minutes: Objectif de temps en minutes (ex: 90 pour 1h30)
    
    Returns:
        TrainingPlan complet
    """
    generator = SemiMarathonPlanGenerator(
        athlete_id=athlete_id,
        start_date=start_date,
        race_date=race_date,
        sessions_per_week=sessions_per_week,
        preferred_days=preferred_days,
        athlete_profile=athlete_profile,
        target_time_minutes=target_time_minutes
    )
    return generator.generate_plan()
