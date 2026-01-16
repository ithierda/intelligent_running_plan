"""
Service Météo
Récupération des prévisions météo pour adapter les recommandations
"""
from pyowm import OWM
from pyowm.commons.exceptions import APIRequestError, UnauthorizedError
from datetime import datetime, date
from typing import Optional, Dict
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


class WeatherService:
    """Service pour récupérer la météo via OpenWeatherMap"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le service météo
        
        Args:
            api_key: Clé API OpenWeatherMap (si None, lit depuis .env)
        """
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        
        if not self.api_key:
            print("⚠️ OPENWEATHER_API_KEY non défini - service météo désactivé")
            self.client = None
            return
        
        try:
            self.client = OWM(self.api_key)
            self.mgr = self.client.weather_manager()
            print("✅ Service météo initialisé")
        except (APIRequestError, UnauthorizedError) as e:
            print(f"❌ Erreur initialisation météo: {e}")
            self.client = None
    
    def get_current_weather(self, location: str = "Paris,FR") -> Optional[Dict]:
        """
        Récupère la météo actuelle
        
        Args:
            location: Ville (format: "Paris,FR")
            
        Returns:
            Dict avec température, conditions, etc.
        """
        if not self.client:
            return None
        
        try:
            observation = self.mgr.weather_at_place(location)
            weather = observation.weather
            
            return {
                'temperature': weather.temperature('celsius')['temp'],
                'feels_like': weather.temperature('celsius')['feels_like'],
                'humidity': weather.humidity,
                'wind_speed': weather.wind()['speed'],
                'status': weather.status,
                'detailed_status': weather.detailed_status,
                'rain': weather.rain.get('1h', 0) if weather.rain else 0,
                'clouds': weather.clouds
            }
        except Exception as e:
            print(f"❌ Erreur récupération météo: {e}")
            return None
    
    def get_forecast(self, location: str = "Paris,FR", target_datetime: Optional[datetime] = None) -> Optional[Dict]:
        """
        Récupère les prévisions météo
        
        Args:
            location: Ville
            target_datetime: Date/heure cible (si None, prochaines heures)
            
        Returns:
            Dict avec prévisions
        """
        if not self.client:
            return None
        
        try:
            forecast = self.mgr.forecast_at_place(location, '3h')
            
            if target_datetime:
                # Trouver la prévision la plus proche
                weather = forecast.get_weather_at(target_datetime)
            else:
                # Prochaine prévision
                weather = forecast.forecast.weathers[0]
            
            return {
                'temperature': weather.temperature('celsius')['temp'],
                'feels_like': weather.temperature('celsius')['feels_like'],
                'humidity': weather.humidity,
                'wind_speed': weather.wind()['speed'],
                'status': weather.status,
                'detailed_status': weather.detailed_status,
                'rain_probability': weather.precipitation_probability if hasattr(weather, 'precipitation_probability') else None,
                'clouds': weather.clouds
            }
        except Exception as e:
            print(f"❌ Erreur récupération prévisions: {e}")
            return None
    
    def is_good_for_running(self, location: str = "Paris,FR", target_datetime: Optional[datetime] = None) -> tuple[bool, str]:
        """
        Détermine si les conditions sont bonnes pour courir
        
        Args:
            location: Ville
            target_datetime: Date/heure cible
            
        Returns:
            (bool, str) : (est_bon, raison)
        """
        weather = self.get_forecast(location, target_datetime) if target_datetime else self.get_current_weather(location)
        
        if not weather:
            return True, "Météo inconnue"
        
        temp = weather['temperature']
        wind = weather['wind_speed']
        rain = weather.get('rain', 0)
        status = weather['status'].lower()
        
        # Conditions défavorables
        if temp < -5:
            return False, f"⚠️ Trop froid ({temp}°C) - Risque de blessure"
        
        if temp > 35:
            return False, f"⚠️ Trop chaud ({temp}°C) - Risque de déshydratation"
        
        if wind > 50:
            return False, f"⚠️ Vent trop fort ({wind} km/h)"
        
        if 'thunderstorm' in status or 'storm' in status:
            return False, "⚠️ Orage - Dangereux"
        
        if rain > 10:
            return False, f"⚠️ Pluie forte ({rain}mm) - Conditions glissantes"
        
        # Conditions moyennes
        if temp < 5:
            return True, f"🥶 Frais ({temp}°C) - Bien se couvrir"
        
        if temp > 28:
            return True, f"🥵 Chaud ({temp}°C) - Bien s'hydrater"
        
        if rain > 2:
            return True, f"🌧️ Pluie légère ({rain}mm) - Prévoir vêtements imperméables"
        
        # Conditions bonnes
        if 10 <= temp <= 20:
            return True, f"✅ Conditions idéales ({temp}°C)"
        
        return True, f"☁️ Conditions acceptables ({temp}°C)"
    
    def get_recommendation(self, location: str = "Paris,FR", target_datetime: Optional[datetime] = None) -> str:
        """
        Génère une recommandation basée sur la météo
        
        Args:
            location: Ville
            target_datetime: Date/heure cible
            
        Returns:
            Recommandation textuelle
        """
        is_good, reason = self.is_good_for_running(location, target_datetime)
        
        weather = self.get_forecast(location, target_datetime) if target_datetime else self.get_current_weather(location)
        
        if not weather:
            return "Météo inconnue - Vérifier les conditions avant de sortir"
        
        recommendation = f"**Météo** : {reason}\n\n"
        
        # Conseils supplémentaires
        temp = weather['temperature']
        
        if temp < 10:
            recommendation += "💡 **Conseil** : Échauffement prolongé, portez des gants et un bonnet\n"
        elif temp > 25:
            recommendation += "💡 **Conseil** : Hydratation renforcée, casquette recommandée\n"
        
        if weather.get('rain', 0) > 0:
            recommendation += "💡 **Équipement** : Veste imperméable, chaussures avec bonne adhérence\n"
        
        if weather['wind_speed'] > 20:
            recommendation += f"💡 **Vent** : {weather['wind_speed']} km/h - Favoriser les parcours protégés\n"
        
        return recommendation


# Helper pour usage simple
def get_weather_service(api_key: Optional[str] = None) -> WeatherService:
    """
    Retourne une instance du service météo
    
    Args:
        api_key: Clé API (optionnel, lit depuis .env)
        
    Returns:
        Instance de WeatherService
    """
    return WeatherService(api_key)
