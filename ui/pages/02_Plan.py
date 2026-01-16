import streamlit as st
import sys
from pathlib import Path
from datetime import date, timedelta

# Ajouter le dossier Project au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.plan_generator import generate_semi_145_plan
from core.plan_generator_5k import generate_5k_plan
from core.plan_generator_10k import generate_10k_plan
from utils.plan_persistence import get_or_create_plan
from utils.ui_helpers import get_jour_name
from utils.profile_persistence import load_profile
from utils.pace_calculator import suggest_race_objective, estimate_race_time

st.set_page_config(page_title="Plan d'entraînement", page_icon="📅", layout="wide")

st.title("📅 Mon Plan d'Entraînement")

# Charger le profil
athlete_profile = load_profile()

# ===== CONFIGURATION DU PLAN =====
if 'training_plan' not in st.session_state or st.session_state.get('show_plan_config', False):
    st.subheader("⚙️ Configuration du plan")
    
    # Réinitialiser le flag après affichage
    if 'show_plan_config' in st.session_state:
        del st.session_state.show_plan_config
    
    # Sélection de distance HORS du formulaire pour mise à jour dynamique
    st.markdown("### 🎯 Objectif")
    distance_choice = st.selectbox(
        "Distance de course",
        options=["5km", "10km", "Semi-marathon"],
        index=2,
        key="distance_choice"
    )
    
    # Durée du plan selon la distance
    if distance_choice == "5km":
        min_weeks, max_weeks = 4, 8
        default_weeks = 6
    elif distance_choice == "10km":
        min_weeks, max_weeks = 6, 12
        default_weeks = 8
    else:  # Semi-marathon
        min_weeks, max_weeks = 10, 15
        default_weeks = 12
    
    with st.form("plan_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            duration_weeks = st.slider(
                f"Durée du plan (semaines)",
                min_value=min_weeks,
                max_value=max_weeks,
                value=default_weeks,
                help=f"Pour {distance_choice}: entre {min_weeks} et {max_weeks} semaines"
            )
            
            race_date = st.date_input(
                "📅 Date de la course",
                value=date.today() + timedelta(weeks=duration_weeks),
                min_value=date.today() + timedelta(weeks=min_weeks),
                help="La date de votre objectif - le plan sera construit rétroactivement"
            )
            
            # Suggestion basée sur VMA si profil disponible
            if athlete_profile and athlete_profile.vma_kmh:
                distance_km = 5 if distance_choice == "5km" else (10 if distance_choice == "10km" else 21.1)
                suggested = suggest_race_objective(distance_km, athlete_profile.vma_kmh)
                est_minutes, est_time = estimate_race_time(distance_km, athlete_profile.vma_kmh)
                
                st.info(f"💡 **Suggestion basée sur votre VMA ({athlete_profile.vma_kmh} km/h)** : {suggested} (≈{est_time})")
            
            # Objectif de temps (selon la distance)
            target_minutes = None
            if distance_choice == "Semi-marathon":
                st.markdown("### ⏱️ Objectif de temps")
                time_options = [
                    ("Sub 1:30", 90),
                    ("Sub 1:35", 95),
                    ("Sub 1:40", 100),
                    ("Sub 1:45", 105),
                    ("Sub 1:50", 110),
                    ("Sub 2:00", 120),
                    ("Finir (sans objectif)", None)
                ]
                time_choice = st.selectbox(
                    "Temps visé",
                    options=[t[0] for t in time_options],
                    index=3  # Sub 1:45 par défaut
                )
                target_minutes = next(t[1] for t in time_options if t[0] == time_choice)
            elif distance_choice == "10km":
                st.markdown("### ⏱️ Objectif de temps")
                time_options_10k = [
                    ("Sub 35min", 35),
                    ("Sub 40min", 40),
                    ("Sub 45min", 45),
                    ("Sub 50min", 50),
                    ("Finir (sans objectif)", None)
                ]
                time_choice = st.selectbox(
                    "Temps visé",
                    options=[t[0] for t in time_options_10k],
                    index=2
                )
                target_minutes = next(t[1] for t in time_options_10k if t[0] == time_choice)
            elif distance_choice == "5km":
                st.markdown("### ⏱️ Objectif de temps")
                time_options_5k = [
                    ("Sub 18min", 18),
                    ("Sub 20min", 20),
                    ("Sub 22min", 22),
                    ("Sub 25min", 25),
                    ("Finir (sans objectif)", None)
                ]
                time_choice = st.selectbox(
                    "Temps visé",
                    options=[t[0] for t in time_options_5k],
                    index=2
                )
                target_minutes = next(t[1] for t in time_options_5k if t[0] == time_choice)
        
        with col2:
            st.markdown("### 📆 Disponibilités")
            sessions_per_week = st.slider(
                "Nombre de séances par semaine",
                min_value=3,
                max_value=6,
                value=4,
                help="Combien de fois par semaine pouvez-vous courir ?"
            )
            
            st.markdown("**Jours préférés pour courir** (sélectionnez-en au moins le nombre de séances)")
            
            col_days1, col_days2 = st.columns(2)
            days_selected = []
            
            with col_days1:
                if st.checkbox("Lundi", value=False):
                    days_selected.append(1)
                if st.checkbox("Mardi", value=True):
                    days_selected.append(2)
                if st.checkbox("Mercredi", value=False):
                    days_selected.append(3)
                if st.checkbox("Jeudi", value=True):
                    days_selected.append(4)
            
            with col_days2:
                if st.checkbox("Vendredi", value=False):
                    days_selected.append(5)
                if st.checkbox("Samedi", value=True):
                    days_selected.append(6)
                if st.checkbox("Dimanche", value=True):
                    days_selected.append(7)
            
            if len(days_selected) < sessions_per_week:
                st.warning(f"⚠️ Sélectionnez au moins {sessions_per_week} jours (vous en avez {len(days_selected)})")
        
        # Bouton de génération
        st.markdown("---")
        submitted = st.form_submit_button(
            "🚀 Générer mon plan d'entraînement",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            if len(days_selected) < sessions_per_week:
                st.error(f"Veuillez sélectionner au moins {sessions_per_week} jours pour vos séances")
            else:
                # Calculer la date de début
                start_date = race_date - timedelta(weeks=duration_weeks)
                
                with st.spinner("🏃 Génération de votre plan personnalisé..."):
                    try:
                        # Générer selon la distance et l'objectif
                        if distance_choice == "5km":
                            st.session_state.training_plan = get_or_create_plan(
                                generate_5k_plan,
                                force_new=True,
                                athlete_id="demo_user",
                                start_date=start_date,
                                race_date=race_date,
                                target_time_minutes=target_minutes,
                                sessions_per_week=sessions_per_week,
                                preferred_days=sorted(days_selected),
                                athlete_profile=athlete_profile  # Passer le profil
                            )
                        elif distance_choice == "10km":
                            st.session_state.training_plan = get_or_create_plan(
                                generate_10k_plan,
                                force_new=True,
                                athlete_id="demo_user",
                                start_date=start_date,
                                race_date=race_date,
                                target_time_minutes=target_minutes,
                                sessions_per_week=sessions_per_week,
                                preferred_days=sorted(days_selected),
                                athlete_profile=athlete_profile  # Passer le profil
                            )
                        else:  # Semi-marathon
                            # Utiliser le générateur avec le profil (allures basées sur VMA)
                            st.session_state.training_plan = get_or_create_plan(
                                generate_semi_145_plan,
                                force_new=True,
                                athlete_id="demo_user",
                                start_date=start_date,
                                race_date=race_date,
                                target_time_minutes=target_minutes,  # Passer l'objectif choisi
                                sessions_per_week=sessions_per_week,
                                preferred_days=sorted(days_selected),
                                athlete_profile=athlete_profile  # Passer le profil
                            )
                        
                        st.success("✅ Plan généré avec succès !")
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la génération : {str(e)}")
                        st.exception(e)

# ===== AFFICHAGE DU PLAN =====
else:
    plan = st.session_state.training_plan
    
    # Bouton pour reconfigurer
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("⚙️ Reconfigurer le plan"):
            st.session_state.show_plan_config = True
            if 'training_plan' in st.session_state:
                del st.session_state.training_plan
            st.rerun()
    
    # Infos générales
    st.subheader("Informations générales")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🎯 Objectif", plan.goal_distance)
    with col2:
        st.metric("⏱️ Temps visé", plan.goal_time)
    with col3:
        st.metric("📅 Durée", f"{len(plan.weeks)} semaines")
    with col4:
        st.metric("🏃 Allure cible", f"{plan.target_pace_per_km}/km")
    
    # Dates
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📍 Début : {plan.start_date.strftime('%d/%m/%Y')}")
    with col2:
        st.info(f"🏁 Course : {plan.end_date.strftime('%d/%m/%Y')}")
    
    # Zones FC personnalisées si profil disponible
    if athlete_profile:
        st.divider()
        with st.expander("📊 Vos zones cardiaques personnalisées", expanded=False):
            from utils.pace_calculator import calculate_heart_rate_zones
            
            fc_max = athlete_profile.get_max_heart_rate()
            fc_repos = athlete_profile.resting_heart_rate
            
            zones = calculate_heart_rate_zones(fc_max, fc_repos)
            
            st.markdown(f"**Basé sur** : FC max {fc_max} bpm" + 
                       (f" • FC repos {fc_repos} bpm (méthode Karvonen)" if fc_repos else " (% FC max)"))
            
            cols = st.columns(5)
            zone_names = ["Z1", "Z2", "Z3", "Z4", "Z5"]
            zone_colors = ["🟢", "🔵", "🟡", "🟠", "🔴"]
            
            for idx, (zone_key, zone_data) in enumerate(zones.items()):
                with cols[idx]:
                    st.markdown(f"{zone_colors[idx]} **{zone_names[idx]}**")
                    st.metric("", f"{zone_data['min']}-{zone_data['max']}", zone_data['description'])
    
    st.divider()
    
    # Afficher les semaines
    st.subheader("Détail du plan")
    
    # Sélecteur de semaine
    week_options = [f"Semaine {i+1} - {week.phase.value}" 
                    for i, week in enumerate(plan.weeks)]
    selected_week_idx = st.selectbox(
        "Sélectionner une semaine",
        range(len(week_options)),
        format_func=lambda x: week_options[x]
    )
    
    week = plan.weeks[selected_week_idx]
    
    # Afficher les séances de la semaine
    st.markdown(f"### Semaine {selected_week_idx + 1} - {week.phase.value}")
    st.write(f"**Type** : {week.week_type.value}")
    st.write(f"📏 Volume total : {week.get_total_volume():.1f} km")
    st.write(f"⏱️ Durée totale : {week.get_total_duration()} min")
    
    st.markdown("---")
    
    for i, session in enumerate(week.sessions, 1):
        jour_name = get_jour_name(session.day_of_week)
        with st.expander(f"📅 {jour_name} - {session.title}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Type** : {session.session_type.value}")
                st.write(f"**Intensité** : {session.intensity.value}")
                st.write(f"**Durée** : {session.duration_minutes} min")
                if session.distance_km:
                    st.write(f"**Distance** : {session.distance_km} km")
                
            with col2:
                if session.is_key_session:
                    st.write("⭐ **Séance clé**")
                st.write(f"**Charge** : {session.load_score}/100")
                if session.scheduled_date:
                    st.write(f"📅 {session.scheduled_date.strftime('%d/%m/%Y')}")
                
            st.write(f"**Description** : {session.description}")
            
            # Afficher la structure si elle existe
            if session.structure:
                st.markdown("**Structure :**")
                summary = session.get_workout_summary()
                if summary:
                    st.code(summary)
                else:
                    for zone in session.structure:
                        rep_str = f"{zone.repetitions}x " if zone.repetitions > 1 else ""
                        if zone.distance_km:
                            st.write(f"• {rep_str}{zone.distance_km}km @ {zone.pace_min_per_km}/km - {zone.description}")
                        elif zone.duration_minutes:
                            st.write(f"• {rep_str}{zone.duration_minutes}min @ {zone.pace_min_per_km}/km - {zone.description}")
    
    # Statistiques
    st.divider()
    with st.expander("📊 Statistiques du plan"):
        stats = plan.get_statistics()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Distribution par type**")
            for session_type, count in stats['session_types'].items():
                st.write(f"• {session_type}: {count} séances")
        
        with col2:
            st.markdown("**Distribution par phase**")
            for phase, count in stats['phases'].items():
                st.write(f"• {phase}: {count} semaines")
        
        with col3:
            st.markdown("**Totaux**")
            st.write(f"• Volume total : {stats['total_volume_km']} km")
            st.write(f"• Nombre de séances : {stats['total_sessions']}")
            st.write(f"• Moyenne/semaine : {stats['total_sessions'] / stats['total_weeks']:.1f} séances")

