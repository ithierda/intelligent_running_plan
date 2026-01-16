import streamlit as st
import sys
from pathlib import Path
from datetime import date, timedelta

# Ajouter le dossier Project au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models.athlete_profile import (
    AthleteProfile, Gender, TrainingLevel, 
    PreferredTerrain, PreferredTime
)
from utils.profile_persistence import save_profile, load_profile, profile_exists

st.set_page_config(page_title="Paramètres", page_icon="⚙️", layout="wide")

st.title("⚙️ Paramètres et Profil")

# Charger ou initialiser le profil
if 'athlete_profile' not in st.session_state:
    existing_profile = load_profile()
    if existing_profile:
        st.session_state.athlete_profile = existing_profile
    else:
        st.session_state.athlete_profile = None

# ===== INFORMATIONS PERSONNELLES =====
st.header("👤 Informations personnelles")

col1, col2 = st.columns(2)

with col1:
    first_name = st.text_input(
        "Prénom *",
        value=st.session_state.athlete_profile.first_name if st.session_state.athlete_profile else "",
        help="Votre prénom"
    )
    
    gender = st.selectbox(
        "Genre *",
        options=[g.value for g in Gender],
        index=0 if not st.session_state.athlete_profile else [g.value for g in Gender].index(st.session_state.athlete_profile.gender.value)
    )
    
    weight = st.number_input(
        "Poids (kg) *",
        min_value=30.0,
        max_value=150.0,
        value=float(st.session_state.athlete_profile.weight_kg) if st.session_state.athlete_profile else 70.0,
        step=0.5,
        help="Votre poids actuel"
    )

with col2:
    last_name = st.text_input(
        "Nom *",
        value=st.session_state.athlete_profile.last_name if st.session_state.athlete_profile else "",
        help="Votre nom de famille"
    )
    
    birth_date_default = st.session_state.athlete_profile.birth_date if st.session_state.athlete_profile else date(1995, 1, 1)
    birth_date = st.date_input(
        "Date de naissance *",
        value=birth_date_default,
        min_value=date(1940, 1, 1),
        max_value=date.today() - timedelta(days=365*10),
        help="Votre date de naissance"
    )
    
    height = st.number_input(
        "Taille (cm)",
        min_value=130,
        max_value=220,
        value=st.session_state.athlete_profile.height_cm if st.session_state.athlete_profile and st.session_state.athlete_profile.height_cm else 175,
        step=1,
        help="Votre taille (optionnel, pour calcul IMC)"
    )

st.divider()

# ===== DONNEES PHYSIOLOGIQUES =====
st.header("❤️ Données physiologiques")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Fréquence cardiaque")
    
    use_custom_fcmax = st.checkbox(
        "J'ai mesuré ma FC max",
        value=st.session_state.athlete_profile.max_heart_rate is not None if st.session_state.athlete_profile else False
    )
    
    if use_custom_fcmax:
        fc_max = st.number_input(
            "FC max mesurée (bpm)",
            min_value=120,
            max_value=220,
            value=st.session_state.athlete_profile.max_heart_rate if st.session_state.athlete_profile and st.session_state.athlete_profile.max_heart_rate else 185,
            help="Si vous avez fait un test à l'effort"
        )
    else:
        # Calculer automatiquement
        age = date.today().year - birth_date.year
        fc_max_calculated = 220 - age
        st.info(f"📊 FC max calculée : **{fc_max_calculated} bpm** (formule : 220 - âge)")
        fc_max = None
    
    fc_repos = st.number_input(
        "FC repos (bpm)",
        min_value=30,
        max_value=100,
        value=st.session_state.athlete_profile.resting_heart_rate if st.session_state.athlete_profile and st.session_state.athlete_profile.resting_heart_rate else 60,
        help="Votre fréquence cardiaque au repos (mesurée au réveil)"
    )

with col2:
    st.subheader("Capacités")
    
    vma = st.number_input(
        "VMA (km/h)",
        min_value=8.0,
        max_value=25.0,
        value=float(st.session_state.athlete_profile.vma_kmh) if st.session_state.athlete_profile and st.session_state.athlete_profile.vma_kmh else 15.0,
        step=0.5,
        help="Vitesse Maximale Aérobie (si vous avez fait un test)"
    )
    
    # Afficher la VO2max estimée
    vo2max_estimated = round(3.5 * vma, 1)
    st.info(f"📊 VO2max estimée : **{vo2max_estimated} ml/min/kg**")
    
    threshold_pace = st.text_input(
        "Allure seuil (min/km)",
        value=st.session_state.athlete_profile.threshold_pace_min_per_km if st.session_state.athlete_profile and st.session_state.athlete_profile.threshold_pace_min_per_km else "",
        placeholder="Ex: 4:30",
        help="Votre allure au seuil anaérobie (optionnel)"
    )

# Afficher les zones FC calculées
if fc_max or birth_date:
    st.divider()
    st.subheader("📊 Vos zones de fréquence cardiaque")
    
    fc_max_to_use = fc_max if fc_max else fc_max_calculated
    
    zones = {
        "Z1 - Récupération": (int(fc_max_to_use * 0.50), int(fc_max_to_use * 0.60)),
        "Z2 - Endurance": (int(fc_max_to_use * 0.60), int(fc_max_to_use * 0.70)),
        "Z3 - Tempo": (int(fc_max_to_use * 0.70), int(fc_max_to_use * 0.80)),
        "Z4 - Seuil": (int(fc_max_to_use * 0.80), int(fc_max_to_use * 0.90)),
        "Z5 - VO2max": (int(fc_max_to_use * 0.90), int(fc_max_to_use * 1.00))
    }
    
    cols = st.columns(5)
    for idx, (zone_name, (min_hr, max_hr)) in enumerate(zones.items()):
        with cols[idx]:
            st.metric(zone_name, f"{min_hr}-{max_hr} bpm")

st.divider()

# ===== NIVEAU ET EXPERIENCE =====
st.header("🏃 Niveau et expérience")

col1, col2 = st.columns(2)

with col1:
    training_level = st.selectbox(
        "Niveau d'entraînement",
        options=[l.value for l in TrainingLevel],
        index=[l.value for l in TrainingLevel].index(st.session_state.athlete_profile.training_level.value) if st.session_state.athlete_profile else 1,
        help="Votre niveau actuel en course à pied"
    )
    
    experience_years = st.number_input(
        "Années d'expérience en course",
        min_value=0,
        max_value=50,
        value=st.session_state.athlete_profile.running_experience_years if st.session_state.athlete_profile and st.session_state.athlete_profile.running_experience_years else 2,
        help="Depuis combien d'années courez-vous régulièrement ?"
    )

with col2:
    preferred_terrain = st.selectbox(
        "Terrain préféré",
        options=[t.value for t in PreferredTerrain],
        index=0 if not st.session_state.athlete_profile else [t.value for t in PreferredTerrain].index(st.session_state.athlete_profile.preferred_terrain.value)
    )
    
    st.markdown("**Moments préférés pour s'entraîner**")
    preferred_times = []
    for time_option in PreferredTime:
        if st.checkbox(
            time_option.value,
            value=time_option in st.session_state.athlete_profile.preferred_training_times if st.session_state.athlete_profile else False,
            key=f"time_{time_option.name}"
        ):
            preferred_times.append(time_option)

st.divider()

# ===== OBJECTIFS =====
st.header("🎯 Objectifs")

main_goal = st.text_input(
    "Objectif principal",
    value=st.session_state.athlete_profile.main_goal if st.session_state.athlete_profile and st.session_state.athlete_profile.main_goal else "",
    placeholder="Ex: Semi-marathon en moins de 1h45",
    help="Votre objectif de course principal"
)

st.markdown("**Objectifs secondaires** (un par ligne)")
secondary_goals_text = st.text_area(
    "Objectifs secondaires",
    value="\n".join(st.session_state.athlete_profile.secondary_goals) if st.session_state.athlete_profile and st.session_state.athlete_profile.secondary_goals else "",
    placeholder="Ex:\n- 10km en moins de 45min\n- Courir 3 fois par semaine",
    height=100,
    label_visibility="collapsed"
)
secondary_goals = [g.strip() for g in secondary_goals_text.split('\n') if g.strip()]

st.divider()

# ===== HISTORIQUE BLESSURES =====
st.header("🏥 Historique médical")

st.markdown("**Blessures actuelles** (une par ligne)")
current_injuries_text = st.text_area(
    "Blessures actuelles",
    value="\n".join(st.session_state.athlete_profile.current_injuries) if st.session_state.athlete_profile and st.session_state.athlete_profile.current_injuries else "",
    placeholder="Ex: Tendinite genou droit",
    height=80,
    label_visibility="collapsed"
)
current_injuries = [i.strip() for i in current_injuries_text.split('\n') if i.strip()]

st.markdown("**Historique des blessures** (une par ligne)")
injury_history_text = st.text_area(
    "Historique blessures",
    value="\n".join(st.session_state.athlete_profile.injury_history) if st.session_state.athlete_profile and st.session_state.athlete_profile.injury_history else "",
    placeholder="Ex: Périostite tibiale (2023)",
    height=80,
    label_visibility="collapsed"
)
injury_history = [i.strip() for i in injury_history_text.split('\n') if i.strip()]

st.divider()

# ===== SAUVEGARDE =====
st.header("💾 Enregistrer le profil")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.button("💾 Sauvegarder mon profil", type="primary", use_container_width=True):
        # Validation
        if not first_name or not last_name:
            st.error("❌ Le prénom et le nom sont obligatoires")
        else:
            # Créer le profil
            profile = AthleteProfile(
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=Gender(gender),
                weight_kg=weight,
                height_cm=height if height > 0 else None,
                max_heart_rate=fc_max,
                resting_heart_rate=fc_repos if fc_repos > 0 else None,
                vma_kmh=vma if vma > 0 else None,
                threshold_pace_min_per_km=threshold_pace if threshold_pace else None,
                training_level=TrainingLevel(training_level),
                running_experience_years=experience_years if experience_years > 0 else None,
                preferred_training_times=preferred_times,
                preferred_terrain=PreferredTerrain(preferred_terrain),
                injury_history=injury_history,
                current_injuries=current_injuries,
                main_goal=main_goal if main_goal else None,
                secondary_goals=secondary_goals
            )
            
            # Sauvegarder
            save_profile(profile)
            st.session_state.athlete_profile = profile
            
            st.success(f"✅ Profil sauvegardé pour {first_name} {last_name} !")
            
            # Afficher un résumé
            with st.expander("📋 Résumé de votre profil"):
                age = profile.get_age()
                fc_max_display = profile.get_max_heart_rate()
                bmi = profile.get_bmi()
                vo2max = profile.estimate_vo2max()
                
                st.write(f"**{first_name} {last_name}**")
                st.write(f"- 🎂 Âge : {age} ans")
                st.write(f"- ⚖️ Poids : {weight} kg")
                if bmi:
                    st.write(f"- � IMC : {bmi}")
                st.write(f"- ❤️ FC max : {fc_max_display} bpm")
                if fc_repos:
                    st.write(f"- 💓 FC repos : {fc_repos} bpm")
                if vma:
                    st.write(f"- 🏃 VMA : {vma} km/h")
                if vo2max:
                    st.write(f"- 📈 VO2max estimée : {vo2max} ml/min/kg")
                st.write(f"- 🎯 Niveau : {training_level}")
                if main_goal:
                    st.write(f"- 🏆 Objectif : {main_goal}")

with col2:
    if st.button("🔄 Réinitialiser", use_container_width=True):
        st.session_state.athlete_profile = None
        st.rerun()

with col3:
    if st.session_state.athlete_profile:
        st.info(f"✅ Profil actif")
    else:
        st.warning("⚠️ Aucun profil")
