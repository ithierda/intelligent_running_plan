"""
Gestion de la persistance du profil athlète
"""
import json
from pathlib import Path
from typing import Optional
from models.athlete_profile import AthleteProfile


DEFAULT_PROFILE_PATH = Path(__file__).parent.parent / "data" / "athlete_profile.json"


def save_profile(profile: AthleteProfile, filepath: Optional[Path] = None) -> None:
    """
    Sauvegarde le profil athlète en JSON
    
    Args:
        profile: Le profil à sauvegarder
        filepath: Chemin du fichier (optionnel, utilise le chemin par défaut si None)
    """
    if filepath is None:
        filepath = DEFAULT_PROFILE_PATH
    
    # Créer le dossier si nécessaire
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Convertir en dict et sauvegarder
    profile_data = profile.to_dict()
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Profil sauvegardé : {filepath}")


def load_profile(filepath: Optional[Path] = None) -> Optional[AthleteProfile]:
    """
    Charge le profil athlète depuis JSON
    
    Args:
        filepath: Chemin du fichier (optionnel, utilise le chemin par défaut si None)
        
    Returns:
        AthleteProfile ou None si le fichier n'existe pas
    """
    if filepath is None:
        filepath = DEFAULT_PROFILE_PATH
    
    if not filepath.exists():
        print(f"⚠️ Aucun profil trouvé à {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        profile = AthleteProfile.from_dict(profile_data)
        print(f"✅ Profil chargé : {profile.first_name} {profile.last_name}")
        return profile
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement du profil : {e}")
        return None


def profile_exists(filepath: Optional[Path] = None) -> bool:
    """
    Vérifie si un profil existe
    
    Args:
        filepath: Chemin du fichier (optionnel)
        
    Returns:
        True si le fichier existe, False sinon
    """
    if filepath is None:
        filepath = DEFAULT_PROFILE_PATH
    
    return filepath.exists()
