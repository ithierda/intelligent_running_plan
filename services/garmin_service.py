"""
Service Garmin Connect
Récupération des données d'entraînement, sommeil, et métriques physiologiques
"""
from garminconnect import Garmin
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List
import os
from dotenv import load_dotenv
from models import DailyMetrics, SleepData, SleepQuality, HeartRateVariability, RestingHeartRate, TrainingLoad

# Charger les variables d'environnement
load_dotenv()


class GarminService:
    """Service pour interagir avec Garmin Connect"""
    
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialise la connexion Garmin
        
        Args:
            email: Email Garmin (si None, lit depuis .env)
            password: Mot de passe Garmin (si None, lit depuis .env)
        """
        self.email = email or os.getenv('GARMIN_EMAIL')
        self.password = password or os.getenv('GARMIN_PASSWORD')
        
        if not self.email or not self.password:
            raise ValueError(
                "GARMIN_EMAIL et GARMIN_PASSWORD doivent être définis dans .env"
            )
        
        self.client: Optional[Garmin] = None
        self._connect()
    
    def _connect(self) -> None:
        """Établit la connexion avec Garmin Connect"""
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            print("✅ Connexion Garmin réussie")
        except Exception as e:
            print(f"❌ Erreur connexion Garmin: {e}")
            raise
    
    def get_sleep_data(self, target_date: date) -> Optional[SleepData]:
        """
        Récupère les données de sommeil
        
        Args:
            target_date: Date du sommeil (nuit précédente)
            
        Returns:
            SleepData ou None si pas de données
        """
        try:
            # Format ISO pour Garmin API
            date_str = target_date.isoformat()
            
            sleep_data = self.client.get_sleep_data(date_str)
            
            if not sleep_data or 'dailySleepDTO' not in sleep_data:
                return None
            
            daily = sleep_data['dailySleepDTO']
            
            # Convertir en heures
            total_sleep_seconds = daily.get('sleepTimeSeconds', 0)
            deep_sleep_seconds = daily.get('deepSleepSeconds', 0)
            light_sleep_seconds = daily.get('lightSleepSeconds', 0)
            rem_sleep_seconds = daily.get('remSleepSeconds', 0)
            awake_seconds = daily.get('awakeSleepSeconds', 0)
            
            total_hours = total_sleep_seconds / 3600
            
            # Score de qualité (basé sur le score Garmin si disponible)
            sleep_score = daily.get('sleepScores', {}).get('overall', {}).get('value')
            
            # Déterminer la qualité
            if sleep_score:
                if sleep_score >= 80:
                    quality = SleepQuality.EXCELLENT
                elif sleep_score >= 70:
                    quality = SleepQuality.GOOD
                elif sleep_score >= 50:
                    quality = SleepQuality.FAIR
                else:
                    quality = SleepQuality.POOR
            else:
                # Fallback basé sur les heures
                if total_hours >= 8:
                    quality = SleepQuality.EXCELLENT
                elif total_hours >= 7:
                    quality = SleepQuality.GOOD
                elif total_hours >= 6:
                    quality = SleepQuality.FAIR
                else:
                    quality = SleepQuality.POOR
            
            return SleepData(
                date=target_date,
                total_sleep_hours=round(total_hours, 1),
                deep_sleep_hours=round(deep_sleep_seconds / 3600, 1),
                light_sleep_hours=round(light_sleep_seconds / 3600, 1),
                rem_sleep_hours=round(rem_sleep_seconds / 3600, 1),
                awake_hours=round(awake_seconds / 3600, 1),
                sleep_quality=quality,
                sleep_score=sleep_score or int(total_hours / 8 * 100)
            )
            
        except Exception as e:
            print(f"❌ Erreur récupération sommeil: {e}")
            return None
    
    def get_hrv_data(self, target_date: date) -> Optional[HeartRateVariability]:
        """
        Récupère les données de variabilité de fréquence cardiaque (HRV)
        
        Args:
            target_date: Date cible
            
        Returns:
            HeartRateVariability ou None
        """
        try:
            date_str = target_date.isoformat()
            
            print(f"🔍 Recherche HRV pour {date_str}...")
            
            # Essayer différentes méthodes selon la version de garminconnect
            hrv_data = None
            try:
                hrv_data = self.client.get_hrv_data(date_str)
                print(f"✅ get_hrv_data a retourné: {type(hrv_data)}")
            except Exception as e:
                print(f"⚠️ get_hrv_data a échoué: {e}")
                # Méthode alternative
                try:
                    stats = self.client.get_stats(date_str)
                    hrv_data = stats
                    print(f"✅ get_stats a retourné: {type(stats)}")
                except Exception as e2:
                    print(f"⚠️ get_stats a aussi échoué: {e2}")
                    return None
            
            if not hrv_data:
                print("❌ hrv_data est None")
                return None
            
            print(f"📋 Clés disponibles: {hrv_data.keys() if isinstance(hrv_data, dict) else 'not a dict'}")
            
            # Chercher dans différentes structures possibles
            hrv_value = None
            weekly_avg = None
            
            if 'hrvSummary' in hrv_data:
                summary = hrv_data['hrvSummary']
                weekly_avg = summary.get('weeklyAvg')
                last_night_avg = summary.get('lastNightAvg')
                hrv_value = last_night_avg or weekly_avg
                print(f"📊 HRV depuis hrvSummary: {hrv_value}")
            elif 'averageHRV' in hrv_data:
                hrv_value = hrv_data['averageHRV']
                print(f"📊 HRV depuis averageHRV: {hrv_value}")
            elif 'hrv' in hrv_data:
                hrv_value = hrv_data['hrv']
                print(f"📊 HRV depuis hrv: {hrv_value}")
            
            if not hrv_value:
                print(f"❌ HRV non trouvé dans les données")
                return None
            
            # Baseline (moyenne des 7 derniers jours)
            baseline = weekly_avg or hrv_value
            
            print(f"✅ HRV trouvé: {hrv_value} ms (baseline: {baseline})")
            
            return HeartRateVariability(
                date=target_date,
                hrv_value=hrv_value,
                baseline_hrv=baseline
            )
            
        except Exception as e:
            print(f"❌ Erreur récupération HRV: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_resting_heart_rate(self, target_date: date) -> Optional[RestingHeartRate]:
        """
        Récupère la fréquence cardiaque au repos
        
        Args:
            target_date: Date cible
            
        Returns:
            RestingHeartRate ou None
        """
        try:
            date_str = target_date.isoformat()
            
            # Stats du jour
            stats = self.client.get_stats(date_str)
            
            if not stats:
                print(f"⚠️ Pas de stats pour {date_str}")
                return None
            
            # Chercher la FC repos dans différents champs possibles
            rhr = (stats.get('restingHeartRate') or 
                   stats.get('minHeartRate') or 
                   stats.get('rhr'))
            
            if not rhr:
                print(f"⚠️ FC repos non trouvée dans: {stats.keys()}")
                return None
            
            print(f"✅ FC repos trouvée: {rhr} bpm")
            
            return RestingHeartRate(
                date=target_date,
                rhr_bpm=rhr
            )
            
        except Exception as e:
            print(f"❌ Erreur récupération FC repos: {e}")
            return None
    
    def get_training_load(self, target_date: date, days_back: int = 28) -> Optional[TrainingLoad]:
        """
        Récupère la charge d'entraînement
        
        Args:
            target_date: Date cible
            days_back: Nombre de jours d'historique pour calculer la charge chronique
            
        Returns:
            TrainingLoad ou None
        """
        try:
            # Récupérer les activités des X derniers jours
            activities = []
            
            for day_offset in range(days_back):
                check_date = target_date - timedelta(days=day_offset)
                date_str = check_date.isoformat()
                
                day_activities = self.client.get_activities_by_date(
                    check_date.strftime('%Y-%m-%d'),
                    check_date.strftime('%Y-%m-%d')
                )
                
                if day_activities:
                    activities.extend(day_activities)
            
            if not activities:
                return None
            
            # Calculer la charge aiguë (7 derniers jours)
            acute_load = 0
            for activity in activities:
                activity_date = datetime.fromisoformat(
                    activity['startTimeLocal'].replace('Z', '+00:00')
                ).date()
                
                days_ago = (target_date - activity_date).days
                
                if days_ago <= 7:
                    # TSS simplifié : durée * intensité relative
                    duration_hours = activity.get('duration', 0) / 3600
                    avg_hr = activity.get('averageHR', 0)
                    
                    # Simplification du TSS
                    if avg_hr > 0:
                        intensity_factor = avg_hr / 180  # Approximation
                        tss = duration_hours * 60 * intensity_factor
                        acute_load += tss
            
            # Charge chronique (28 derniers jours)
            chronic_load = 0
            for activity in activities:
                duration_hours = activity.get('duration', 0) / 3600
                avg_hr = activity.get('averageHR', 0)
                
                if avg_hr > 0:
                    intensity_factor = avg_hr / 180
                    tss = duration_hours * 60 * intensity_factor
                    chronic_load += tss
            
            # Moyennes
            acute_avg = acute_load / 7
            chronic_avg = chronic_load / 28
            
            return TrainingLoad(
                date=target_date,
                acute_load=round(acute_avg, 1),
                chronic_load=round(chronic_avg, 1)
            )
            
        except Exception as e:
            print(f"❌ Erreur récupération charge: {e}")
            return None
    
    def get_daily_metrics(self, target_date: date) -> Optional[DailyMetrics]:
        """
        Récupère toutes les métriques du jour
        
        Args:
            target_date: Date cible
            
        Returns:
            DailyMetrics complet
        """
        sleep = self.get_sleep_data(target_date)
        hrv = self.get_hrv_data(target_date)
        rhr = self.get_resting_heart_rate(target_date)
        load = self.get_training_load(target_date)
        
        if not sleep:
            return None
        
        return DailyMetrics(
            date=target_date,
            sleep=sleep,
            hrv=hrv,
            rhr=rhr,
            training_load=load
        )
    
    def get_body_battery(self, target_date: date) -> Optional[int]:
        """
        Récupère le Body Battery Garmin (si disponible)
        
        Args:
            target_date: Date cible
            
        Returns:
            Score Body Battery (0-100) ou None
        """
        try:
            date_str = target_date.isoformat()
            stats = self.client.get_stats(date_str)
            
            if not stats:
                return None
            
            # Body Battery peut être dans différentes clés selon le modèle
            body_battery = stats.get('bodyBatteryMostRecentValue')
            
            return body_battery
            
        except Exception as e:
            print(f"❌ Erreur récupération Body Battery: {e}")
            return None
    
    def get_last_activity(self, limit: int = 1) -> Optional[Dict]:
        """
        Récupère la ou les dernières activités
        
        Args:
            limit: Nombre d'activités à récupérer
            
        Returns:
            Dict avec les infos de la dernière activité ou None
        """
        try:
            activities = self.client.get_activities(0, limit)
            
            if not activities or len(activities) == 0:
                return None
            
            last_activity = activities[0]
            
            # Parser les infos importantes
            activity_info = {
                'activity_id': last_activity.get('activityId'),
                'activity_name': last_activity.get('activityName'),
                'activity_type': last_activity.get('activityType', {}).get('typeKey', 'unknown'),
                'start_time': last_activity.get('startTimeLocal'),
                'distance_km': round(last_activity.get('distance', 0) / 1000, 2),
                'duration_seconds': last_activity.get('duration', 0),
                'duration_minutes': round(last_activity.get('duration', 0) / 60, 1),
                'avg_hr': last_activity.get('averageHR'),
                'max_hr': last_activity.get('maxHR'),
                'avg_pace': last_activity.get('averageSpeed'),  # m/s
                'calories': last_activity.get('calories'),
                'elevation_gain': last_activity.get('elevationGain'),
                'avg_cadence': last_activity.get('averageRunningCadenceInStepsPerMinute'),
            }
            
            # Convertir la vitesse en allure (min/km)
            if activity_info['avg_pace'] and activity_info['avg_pace'] > 0:
                # m/s -> km/h -> min/km
                speed_kmh = activity_info['avg_pace'] * 3.6
                if speed_kmh > 0:
                    pace_min_per_km = 60 / speed_kmh
                    minutes = int(pace_min_per_km)
                    seconds = int((pace_min_per_km - minutes) * 60)
                    activity_info['pace_str'] = f"{minutes}:{seconds:02d}/km"
                    activity_info['avg_pace_seconds'] = pace_min_per_km * 60  # Stocker en secondes pour calculs
                else:
                    activity_info['pace_str'] = "N/A"
                    activity_info['avg_pace_seconds'] = None
            else:
                activity_info['pace_str'] = "N/A"
                activity_info['avg_pace_seconds'] = None
            
            return activity_info
            
        except Exception as e:
            print(f"❌ Erreur récupération dernière activité: {e}")
            return None
    
    def get_recent_activities(self, limit: int = 5) -> List[Dict]:
        """
        Récupère les N dernières activités
        
        Args:
            limit: Nombre d'activités à récupérer (défaut 5)
            
        Returns:
            Liste de dictionnaires avec les infos des activités
        """
        try:
            activities = self.client.get_activities(0, limit)
            
            if not activities or len(activities) == 0:
                return []
            
            parsed_activities = []
            
            for activity in activities:
                # Parser les infos importantes
                activity_info = {
                    'activity_id': activity.get('activityId'),
                    'activity_name': activity.get('activityName'),
                    'activity_type': activity.get('activityType', {}).get('typeKey', 'unknown'),
                    'start_time': activity.get('startTimeLocal'),
                    'distance_km': round(activity.get('distance', 0) / 1000, 2),
                    'duration_seconds': activity.get('duration', 0),
                    'duration_minutes': round(activity.get('duration', 0) / 60, 1),
                    'avg_hr': activity.get('averageHR'),
                    'max_hr': activity.get('maxHR'),
                    'avg_pace': activity.get('averageSpeed'),  # m/s
                    'calories': activity.get('calories'),
                    'elevation_gain': activity.get('elevationGain'),
                    'avg_cadence': activity.get('averageRunningCadenceInStepsPerMinute'),
                }
                
                # Convertir la vitesse en allure (min/km)
                if activity_info['avg_pace'] and activity_info['avg_pace'] > 0:
                    # m/s -> km/h -> min/km
                    speed_kmh = activity_info['avg_pace'] * 3.6
                    if speed_kmh > 0:
                        pace_min_per_km = 60 / speed_kmh
                        minutes = int(pace_min_per_km)
                        seconds = int((pace_min_per_km - minutes) * 60)
                        activity_info['pace_str'] = f"{minutes}:{seconds:02d}/km"
                        activity_info['avg_pace_seconds'] = pace_min_per_km * 60  # En secondes pour calculs
                    else:
                        activity_info['pace_str'] = "N/A"
                        activity_info['avg_pace_seconds'] = None
                else:
                    activity_info['pace_str'] = "N/A"
                    activity_info['avg_pace_seconds'] = None
                
                parsed_activities.append(activity_info)
            
            return parsed_activities
            
        except Exception as e:
            print(f"❌ Erreur récupération activités récentes: {e}")
            return []


# Helper pour usage simple
def get_garmin_service(email: Optional[str] = None, password: Optional[str] = None) -> GarminService:
    """
    Retourne une instance du service Garmin
    
    Args:
        email: Email Garmin (optionnel, lit depuis .env)
        password: Mot de passe (optionnel, lit depuis .env)
        
    Returns:
        Instance de GarminService
    """
    return GarminService(email, password)
