import streamlit as st
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Ajouter le dossier Project au path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.session_adapter import quick_adapt
from models import DailyMetrics, SleepData, SleepQuality, SubjectiveMetrics
from models.session import EXAMPLE_SESSIONS
from services.garmin_service import get_garmin_service
from utils.plan_helpers import get_session_for_date, get_current_week_number
from utils.feedback_analyzer import get_recent_feedback_impact, should_force_rest
from utils.activity_load import calculate_acwr_from_recent_activities, adjust_recovery_score_for_activity
from utils.plan_persistence import load_plan_from_json
from utils.ui_helpers import get_jour_name
from utils.profile_persistence import load_profile

st.set_page_config(page_title="Séance du jour", page_icon="🎯", layout="wide")

st.title("🎯 Votre séance du jour")

# Charger le profil
athlete_profile = load_profile()

# ===== SESSION STATE =====
if 'use_garmin' not in st.session_state:
    st.session_state.use_garmin = False
if 'garmin_metrics' not in st.session_state:
    st.session_state.garmin_metrics = None
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = None

# ===== TOGGLE GARMIN =====
col1, col2 = st.columns([3, 1])
with col2:
    use_garmin = st.toggle("📱 Utiliser Garmin", value=st.session_state.use_garmin)
    if use_garmin != st.session_state.use_garmin:
        st.session_state.use_garmin = use_garmin
        st.session_state.garmin_metrics = None
        st.session_state.last_activity = None

# ===== MODE GARMIN =====
metrics = None
if use_garmin:
    st.subheader("📱 Données Garmin")
    
    # Charger seulement si pas en cache
    if st.session_state.garmin_metrics is None:
        with st.spinner("Récupération des données Garmin..."):
            try:
                garmin_service = get_garmin_service()
                metrics = garmin_service.get_daily_metrics(date.today())
                
                if metrics:
                    st.session_state.garmin_metrics = metrics
                    st.success("✅ Données Garmin récupérées")
                else:
                    st.warning("Aucune donnée Garmin disponible pour aujourd'hui")
                    
                # Récupérer la dernière activité
                last_activity = garmin_service.get_last_activity()
                st.session_state.last_activity = last_activity
                    
            except Exception as e:
                st.error(f"❌ Erreur Garmin : {str(e)}")
    else:
        metrics = st.session_state.garmin_metrics
        st.info("📦 Données en cache (rechargez la page pour actualiser)")
    
    # AFFICHER LES METRIQUES (que ce soit premier chargement ou cache)
    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "😴 Sommeil",
                f"{metrics.sleep.total_sleep_hours}h",
                f"Score: {metrics.sleep.sleep_score}"
            )
        
        with col2:
            if metrics.hrv:
                deviation = ((metrics.hrv.hrv_value - metrics.hrv.baseline_hrv) / metrics.hrv.baseline_hrv * 100)
                st.metric("❤️ HRV", f"{metrics.hrv.hrv_value} ms", f"{deviation:+.0f}%")
            else:
                st.metric("❤️ HRV", "N/A", help="Votre montre ne supporte pas HRV")
        
        with col3:
            if metrics.rhr:
                st.metric("💓 FC repos", f"{metrics.rhr.rhr_bpm} bpm")
            else:
                st.metric("💓 FC repos", "N/A")
        
        with col4:
            if metrics.training_load:
                acwr = metrics.training_load.calculate_acwr()
                st.metric(
                    "📊 ACWR",
                    f"{acwr:.2f}",
                    "⚠️ Fatigue" if acwr > 1.5 else "✅ OK"
                )
            else:
                st.metric("📊 Charge", "N/A")
    
    # AFFICHER LA DERNIERE ACTIVITE (que ce soit premier chargement ou cache)
    if st.session_state.last_activity:
        st.divider()
        st.subheader("🏃 Dernière activité enregistrée")
        last_activity = st.session_state.last_activity
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📅 Date", last_activity['start_time'][:10])
            st.metric("🏃 Type", last_activity['activity_type'])
        
        with col2:
            st.metric("📏 Distance", f"{last_activity['distance_km']} km")
            st.metric("⏱️ Durée", f"{last_activity['duration_minutes']} min")
        
        with col3:
            st.metric("⚡ Allure", last_activity['pace_str'])
            if last_activity['avg_cadence']:
                st.metric("👟 Cadence", f"{last_activity['avg_cadence']} spm")
        
        with col4:
            if last_activity['avg_hr']:
                st.metric("❤️ FC moy", f"{last_activity['avg_hr']} bpm")
            if last_activity['max_hr']:
                st.metric("💓 FC max", f"{last_activity['max_hr']} bpm")
        
        # Infos additionnelles
        extra_info = []
        if last_activity['calories']:
            extra_info.append(f"🔥 **Calories** : {last_activity['calories']} kcal")
        if last_activity['elevation_gain']:
            extra_info.append(f"⛰️ **Dénivelé+** : {last_activity['elevation_gain']} m")
        
        if extra_info:
            st.write(" • ".join(extra_info))
        
        # === FEEDBACK SUBJECTIF SUR L'ACTIVITÉ ===
        st.divider()
        st.subheader("💭 Comment s'est passée cette séance ?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**😊 Sensations positives**")
            positive_feedback = {}
            positive_feedback['kiffe'] = st.checkbox("🤩 J'ai kiffé ! C'était génial")
            positive_feedback['jambes_legeres'] = st.checkbox("🦵 Les jambes avançaient toutes seules")
            positive_feedback['bonne_forme'] = st.checkbox("💪 En super forme")
            positive_feedback['mental_top'] = st.checkbox("🧠 Mental au top")
            positive_feedback['plaisir'] = st.checkbox("😄 Beaucoup de plaisir")
        
        with col2:
            st.markdown("**😓 Difficultés rencontrées**")
            negative_feedback = {}
            negative_feedback['jambes_lourdes'] = st.checkbox("🦵 Jambes lourdes")
            negative_feedback['pluie'] = st.checkbox("🌧️ Il pleuvait beaucoup")
            negative_feedback['enrhume'] = st.checkbox("🤧 J'étais enrhumé")
            negative_feedback['fatigue'] = st.checkbox("😴 Très fatigué")
            negative_feedback['douleurs'] = st.checkbox("😣 Douleurs/courbatures")
            negative_feedback['mauvaise_journee'] = st.checkbox("😞 Mauvaise journée")
            negative_feedback['chaleur'] = st.checkbox("🥵 Trop chaud")
            negative_feedback['froid'] = st.checkbox("🥶 Trop froid")
        
        # Zone de commentaire libre
        st.markdown("**📝 Notes personnelles**")
        activity_notes = st.text_area(
            "Ajoutez vos commentaires (optionnel)",
            placeholder="Ex: Première sortie avec les nouvelles chaussures, parcours vallonné, vent de face...",
            height=100
        )
        
        # Bouton pour sauvegarder le feedback
        if st.button("💾 Enregistrer mon feedback", type="secondary"):
            # Construire le résumé du feedback
            positive_items = [k for k, v in positive_feedback.items() if v]
            negative_items = [k for k, v in negative_feedback.items() if v]
            
            feedback_summary = {
                'activity_date': last_activity['start_time'][:10],
                'positive': positive_items,
                'negative': negative_items,
                'notes': activity_notes
            }
            
            # Stocker dans session_state (plus tard on pourra sauvegarder dans un fichier)
            if 'activity_feedbacks' not in st.session_state:
                st.session_state.activity_feedbacks = []
            
            st.session_state.activity_feedbacks.append(feedback_summary)
            
            st.success("✅ Feedback enregistré ! Ces informations aideront à mieux adapter vos futures séances.")
            
            # Afficher un résumé
            if positive_items or negative_items or activity_notes:
                with st.expander("📊 Résumé de votre feedback"):
                    if positive_items:
                        st.write("**Points positifs :**")
                        for item in positive_items:
                            st.write(f"  • {item.replace('_', ' ').title()}")
                    if negative_items:
                        st.write("**Points négatifs :**")
                        for item in negative_items:
                            st.write(f"  • {item.replace('_', ' ').title()}")
                    if activity_notes:
                        st.write(f"**Notes :** {activity_notes}")

# ===== RESSENTI SUBJECTIF (TOUJOURS AFFICHÉ) =====
st.divider()
st.subheader("💭 Votre ressenti personnel")
st.write("Donnez-nous votre avis sur votre forme actuelle - cela complète les données objectives")

col1, col2 = st.columns(2)
with col1:
    motivation = st.slider("� Motivation", 1, 5, 3, help="Votre envie de vous entraîner aujourd'hui")
    energy = st.slider("⚡ Énergie", 1, 5, 3, help="Votre niveau d'énergie général")

with col2:
    muscle_soreness = st.slider("🦵 Courbatures", 1, 5, 2, help="1 = Aucune, 5 = Très douloureuses")
    mood = st.slider("😊 Humeur", 1, 5, 3, help="Votre état d'esprit général")

# Stocker les métriques subjectives
if not metrics:
    # Si pas de Garmin, on crée des métriques complètes avec des valeurs par défaut
    metrics = DailyMetrics(
        date=date.today(),
        sleep=SleepData(
            date=date.today(),
            total_sleep_hours=7.5,
            sleep_quality=SleepQuality.GOOD,
            sleep_score=90
        ),
        subjective=SubjectiveMetrics(
            date=date.today(),
            motivation=motivation,
            energy=energy,
            muscle_soreness=muscle_soreness,
            mood=mood
        )
    )
else:
    # Si Garmin existe, on met à jour juste les subjectives
    metrics.subjective = SubjectiveMetrics(
        date=date.today(),
        motivation=motivation,
        energy=energy,
        muscle_soreness=muscle_soreness,
        mood=mood
    )

# ===== ANALYSE =====
st.divider()

# Charger le plan s'il n'est pas en session_state
if 'training_plan' not in st.session_state:
    # Essayer de charger depuis JSON
    plan = load_plan_from_json()
    if plan:
        st.session_state.training_plan = plan
        st.success(f"✅ Plan {plan.goal_distance} chargé automatiquement")

# Afficher la séance prévue aujourd'hui
if 'training_plan' in st.session_state:
    plan = st.session_state.training_plan
    today_session = get_session_for_date(plan, date.today())
    week_num = get_current_week_number(plan, date.today())
    
    if today_session:
        # Nom du jour
        jour_name = get_jour_name(today_session.day_of_week)
        
        st.subheader(f"📋 Séance prévue - {jour_name} (Semaine {week_num}/{plan.duration_weeks})")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏃 Type", today_session.session_type.value)
        with col2:
            st.metric("⚡ Intensité", today_session.intensity.value)
        with col3:
            st.metric("📏 Distance", f"{today_session.distance_km} km")
        with col4:
            st.metric("⏱️ Durée", f"{today_session.duration_minutes} min")
        
        with st.expander("📖 Voir les détails de la séance"):
            st.write(f"**{today_session.title}**")
            st.write(today_session.description)
            
            if today_session.structure:
                st.markdown("**Structure :**")
                summary = today_session.get_workout_summary()
                if summary:
                    st.code(summary)
            
            # Afficher les allures personnalisées si VMA disponible
            if athlete_profile and athlete_profile.vma_kmh:
                st.markdown("---")
                st.markdown("**💡 Vos allures personnalisées (basées sur votre VMA)**")
                
                from utils.pace_calculator import calculate_training_paces_from_vma, seconds_to_pace
                
                # Passer tous les paramètres pour ajustement correct
                paces = calculate_training_paces_from_vma(
                    athlete_profile.vma_kmh,
                    fc_max=athlete_profile.max_heart_rate,
                    fc_repos=athlete_profile.resting_heart_rate,
                    level=athlete_profile.training_level
                )
                
                pace_cols = st.columns(4)
                
                with pace_cols[0]:
                    st.caption("🟢 Récupération")
                    # Les paces sont déjà au format "M:SS"
                    st.write(f"{paces['recovery']['min']} - {paces['recovery']['max']}")
                
                with pace_cols[1]:
                    st.caption("🔵 Endurance")
                    st.write(f"{paces['endurance']['min']} - {paces['endurance']['max']}")
                
                with pace_cols[2]:
                    st.caption("🟡 Tempo")
                    st.write(f"{paces['tempo']['min']} - {paces['tempo']['max']}")
                
                with pace_cols[3]:
                    st.caption("🔴 Seuil/VMA")
                    st.write(f"{paces['threshold']['min']} - {paces['vma']['max']}")
        
        st.divider()
    else:
        st.info("🏖️ Pas de séance prévue aujourd'hui - Jour de repos !")
        st.divider()
else:
    st.warning("💡 Aucun plan d'entraînement trouvé. Allez dans la page 'Plan' pour en générer un !")
    st.divider()

if metrics and st.button("🔍 Analyser ma récupération", type="primary"):
    recovery_score = metrics.calculate_recovery_score()
    
    # ===== NOUVEAU : Intégrer l'activité du jour si présente =====
    activity_penalty = {'adjusted_score': recovery_score, 'penalty': 0, 'details': []}
    acwr_info = None
    
    if st.session_state.last_activity:
        # Calculer ACWR et charge
        acwr_info = calculate_acwr_from_recent_activities(
            st.session_state.last_activity
        )
        
        # Calculer combien de temps s'est écoulé depuis l'activité
        activity_start = st.session_state.last_activity.get('start_time')
        if isinstance(activity_start, str):
            activity_dt = datetime.fromisoformat(activity_start.replace('Z', '+00:00'))
            hours_since = (datetime.now(activity_dt.tzinfo) - activity_dt).total_seconds() / 3600
        else:
            hours_since = 2.0  # Estimation par défaut
        
        # Ajuster le score avec la fatigue de l'activité
        activity_penalty = adjust_recovery_score_for_activity(
            recovery_score,
            acwr_info,
            hours_since
        )
        
        recovery_score = activity_penalty['adjusted_score']
    
    # ===== Intégrer les feedbacks des activités récentes =====
    feedback_impact = {'score_adjustment': 0, 'details': [], 'warnings': []}
    
    if 'activity_feedbacks' in st.session_state and st.session_state.activity_feedbacks:
        feedback_impact = get_recent_feedback_impact(st.session_state.activity_feedbacks, days_lookback=2)
        
        # Ajuster le score de récupération
        recovery_score += feedback_impact['score_adjustment']
        recovery_score = max(0, min(100, recovery_score))  # Clamper entre 0-100
        
        # Afficher l'impact des feedbacks
        if feedback_impact['details']:
            with st.expander("📝 Impact de vos feedbacks récents"):
                for detail in feedback_impact['details']:
                    st.write(detail)
                st.write(f"**Ajustement total : {feedback_impact['score_adjustment']:+.1f} points**")
        
        # Afficher les warnings
        for warning in feedback_impact['warnings']:
            st.warning(warning)
        
        # Forcer le repos si nécessaire
        if should_force_rest(st.session_state.activity_feedbacks):
            st.error("🚨 REPOS OBLIGATOIRE - Vos feedbacks récents indiquent un besoin impératif de récupération !")
    
    # Stocker dans session_state
    st.session_state.recovery_score = recovery_score
    st.session_state.metrics = metrics
    st.session_state.feedback_impact = feedback_impact
    st.session_state.activity_penalty = activity_penalty
    st.session_state.acwr_info = acwr_info
    
    # Récupérer la séance du jour depuis le plan (ou fallback sur exemple)
    session = None
    
    # Vérifier si un plan existe
    if 'training_plan' in st.session_state:
        plan = st.session_state.training_plan
        session = get_session_for_date(plan, date.today())
        week_num = get_current_week_number(plan, date.today())
        
        if session:
            st.session_state.current_week = week_num
            st.info(f"📅 Semaine {week_num}/12 - {plan.weeks[week_num-1].phase.value}")
        else:
            st.warning("⚠️ Pas de séance prévue aujourd'hui selon votre plan. Utilisez une séance d'exemple.")
    
    # Fallback si pas de plan ou pas de séance aujourd'hui
    if session is None:
        st.warning("💡 Aucun plan d'entraînement trouvé. Allez dans la page 'Plan' pour en générer un !")
        session = EXAMPLE_SESSIONS["threshold_3x10"]
        st.info("Utilisation d'une séance d'exemple pour la démonstration.")
    
    # Adapter la séance
    rec = quick_adapt(session, recovery_score, has_time=True)
    
    st.session_state.session = session
    st.session_state.rec = rec

# ===== RÉSULTATS =====
if 'rec' in st.session_state:
    rec = st.session_state.rec
    session = st.session_state.session
    recovery_score = st.session_state.recovery_score
    
    st.subheader("📊 Score de récupération")
    
    # Afficher le score avec indication de l'impact des feedbacks
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.metric("Score global", f"{recovery_score:.0f}/100")
        st.progress(recovery_score / 100)
    
    with col2:
        if 'feedback_impact' in st.session_state:
            impact = st.session_state.feedback_impact
            if impact['score_adjustment'] != 0:
                delta_color = "normal" if impact['score_adjustment'] > 0 else "inverse"
                st.metric(
                    "Impact feedbacks",
                    f"{impact['score_adjustment']:+.0f} pts",
                    delta_color=delta_color
                )
    
    with col3:
        # Afficher l'impact de l'activité du jour si présente
        if st.session_state.last_activity and 'activity_penalty' in st.session_state:
            penalty = st.session_state.activity_penalty['penalty']
            if penalty != 0:
                st.metric(
                    "Fatigue activité",
                    f"{penalty:+.0f} pts",
                    delta_color="inverse"
                )
    
    with st.expander("Voir le détail du calcul"):
        metrics = st.session_state.metrics
        st.write("**Base (métriques physiologiques) :**")
        st.write(f"- Sommeil (35%) : {metrics.sleep.get_normalized_score() * 35:.1f}/35")
        if metrics.hrv:
            st.write(f"- HRV (25%) : {metrics.hrv.get_normalized_score() * 25:.1f}/25")
        if metrics.rhr:
            st.write(f"- FC repos (10%) : {metrics.rhr.get_normalized_score() * 10:.1f}/10")
        if metrics.training_load:
            st.write(f"- Charge (20%) : {metrics.training_load.get_normalized_score() * 20:.1f}/20")
        if metrics.subjective:
            st.write(f"- Subjectif (10%) : {metrics.subjective.get_normalized_score() * 10:.1f}/10")
        
        # Afficher l'impact de l'activité du matin
        if st.session_state.last_activity and 'activity_penalty' in st.session_state:
            st.write("")
            st.write("**Impact de l'activité du jour :**")
            penalty_info = st.session_state.activity_penalty
            for detail in penalty_info['details']:
                st.write(detail)
        
        # Afficher l'ACWR si calculé
        if 'acwr_info' in st.session_state and st.session_state.acwr_info:
            acwr = st.session_state.acwr_info
            st.write("")
            st.write("**Charge d'entraînement (ACWR) :**")
            st.write(f"- Charge aujourd'hui : {acwr['today_load']:.0f}")
            st.write(f"- ACWR : {acwr['acwr']:.2f} ({acwr['status']})")
            st.write(f"- Risque blessure : {acwr['risk']}")
        
        # Afficher l'ajustement feedback
        if 'feedback_impact' in st.session_state:
            impact = st.session_state.feedback_impact
            if impact['score_adjustment'] != 0:
                st.write("")
                st.write("**Ajustement basé sur vos feedbacks :**")
                st.write(f"- Impact total : **{impact['score_adjustment']:+.1f} points**")
    
    st.divider()
    
    # Recommandation
    action_colors = {
        "Maintenir": "🟢",
        "Maintenir avec surveillance": "🟡",
        "Alléger": "🟠",
        "Remplacer": "🔴",
        "Reporter": "🔵",
        "Annuler": "⚫"
    }
    
    st.subheader(f"{action_colors.get(rec.action.value, '')} {rec.action.value}")
    
    if rec.action.value == "Maintenir":
        st.success(rec.reason)
    elif rec.action.value == "Maintenir avec surveillance":
        st.info(rec.reason)
    elif rec.action.value in ["Alléger", "Remplacer"]:
        st.warning(rec.reason)
    else:
        st.error(rec.reason)
    
    # Séance
    final_session = rec.modified_session if rec.modified_session else session
    
    st.divider()
    st.subheader("📋 Votre séance")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏃 Type", final_session.session_type.value)
    with col2:
        st.metric("📏 Distance", f"{final_session.distance_km} km")
    with col3:
        st.metric("⏱️ Durée", f"{final_session.duration_minutes} min")
    
    st.write(f"**{final_session.title}**")
    st.write(final_session.description)
    
    if final_session.structure:
        with st.expander("📊 Voir la structure détaillée"):
            for i, zone in enumerate(final_session.structure, 1):
                st.write(f"**{i}. {zone.description}**")
                if zone.distance_km:
                    st.write(f"   • Distance : {zone.distance_km} km")
                if zone.duration_minutes:
                    st.write(f"   • Durée : {zone.duration_minutes} min")
                st.write(f"   • Allure : {zone.pace_min_per_km}/km")
                if zone.repetitions > 1:
                    st.write(f"   • Répétitions : {zone.repetitions}x")
                if zone.recovery_minutes:
                    st.write(f"   • Récupération : {zone.recovery_minutes} min")
    
    # ===== CALENDRIER =====
    st.divider()
    st.subheader("📅 Ajouter au calendrier")
    
    with st.form("calendar_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            time_options = [f"{h:02d}:00" for h in range(6, 22)]
            selected_time = st.selectbox(
                "⏰ Heure de la séance",
                time_options,
                index=12
            )
        
        with col2:
            st.write("")
            st.write("")
            add_to_calendar = st.form_submit_button("📅 Ajouter", type="primary", use_container_width=True)
    
    if add_to_calendar:
        try:
            with st.spinner("Ajout au calendrier..."):
                hour, minute = map(int, selected_time.split(':'))
                start_dt = datetime.combine(date.today(), datetime.min.time().replace(hour=hour, minute=minute))
                end_dt = start_dt + timedelta(minutes=final_session.duration_minutes)
                
                description = f"""{final_session.description}

📊 Détails:
- Type: {final_session.session_type.value}
- Intensité: {final_session.intensity.value}
- Distance: {final_session.distance_km} km
- Durée: {final_session.duration_minutes} min

🎯 Score de récupération: {recovery_score:.0f}/100
💡 Recommandation: {rec.action.value}

{rec.reason}
"""
                
                SERVICE_ACCOUNT_FILE = 'service_account.json'
                SCOPES = ['https://www.googleapis.com/auth/calendar']
                CALENDAR_ID = 'ithier.da@gmail.com'
                
                credentials = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES
                )
                service = build('calendar', 'v3', credentials=credentials)
                
                event = {
                    'summary': f"🏃 {final_session.title}",
                    'description': description.strip(),
                    'start': {
                        'dateTime': start_dt.isoformat(),
                        'timeZone': 'Europe/Paris'
                    },
                    'end': {
                        'dateTime': end_dt.isoformat(),
                        'timeZone': 'Europe/Paris'
                    },
                    'colorId': '4'
                }
                
                created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
                
                st.success("✅ Séance ajoutée à votre calendrier !")
                st.write(f"🔗 [Voir dans Google Calendar]({created.get('htmlLink', '#')})")
                
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            st.code(traceback.format_exc())