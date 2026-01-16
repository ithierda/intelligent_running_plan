import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Ajouter le dossier Project au path AVANT les imports locaux
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.plan_persistence import load_plan_from_json
from utils.profile_persistence import load_profile
from services.garmin_service import get_garmin_service
from models.session import SessionStatus
from utils.ui_helpers import get_jour_name


st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Tableau de bord")

# Charger le profil athlète
athlete_profile = load_profile()

# Afficher le profil si disponible
if athlete_profile:
    st.markdown(f"### 👋 Bonjour **{athlete_profile.first_name}** !")
    
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    
    with col_p1:
        age = athlete_profile.get_age()
        st.metric("🎂 Âge", f"{age} ans")
    
    with col_p2:
        if athlete_profile.vma_kmh:
            st.metric("🏃 VMA", f"{athlete_profile.vma_kmh} km/h")
            vo2max = athlete_profile.estimate_vo2max()
            if vo2max:
                st.caption(f"VO2max: {vo2max} ml/min/kg")
        else:
            st.metric("🏃 VMA", "Non renseignée")
    
    with col_p3:
        fc_max = athlete_profile.get_max_heart_rate()
        st.metric("❤️ FC max", f"{fc_max} bpm")
        if athlete_profile.resting_heart_rate:
            st.caption(f"FC repos: {athlete_profile.resting_heart_rate} bpm")
    
    with col_p4:
        if athlete_profile.main_goal:
            st.metric("🎯 Objectif", athlete_profile.main_goal)
        else:
            st.metric("🎯 Objectif", "Non défini")
    
    st.divider()
else:
    st.info("💡 Créez votre profil dans la page **Settings** pour une expérience personnalisée !")
    st.divider()

# Charger le plan
plan = None
if 'training_plan' not in st.session_state:
    plan = load_plan_from_json()
    if plan:
        st.session_state.training_plan = plan
else:
    plan = st.session_state.training_plan

# Si pas de plan, afficher message
if not plan:
    st.warning("⚠️ Aucun plan d'entraînement actif. Rendez-vous dans la page **Plan** pour en créer un !")
    st.stop()

# ===== VUE D'ENSEMBLE DU PLAN =====
st.header(f"🎯 {plan.name}")

col1, col2, col3, col4 = st.columns(4)

# Calculer les statistiques
today = date.today()
days_elapsed = (today - plan.start_date).days
days_total = (plan.end_date - plan.start_date).days
progress_pct = min(100, int((days_elapsed / days_total) * 100)) if days_total > 0 else 0

total_sessions = sum(len(week.sessions) for week in plan.weeks)
completed_sessions = sum(
    1 for week in plan.weeks 
    for session in week.sessions 
    if session.status == SessionStatus.COMPLETED
)

total_distance = sum(
    week.sessions[i].distance_km 
    for week in plan.weeks 
    for i in range(len(week.sessions))
)

completed_distance = sum(
    session.actual_distance_km or 0
    for week in plan.weeks
    for session in week.sessions
    if session.status == SessionStatus.COMPLETED
)

with col1:
    st.metric(
        "📅 Progression",
        f"{progress_pct}%",
        f"{days_elapsed}/{days_total} jours"
    )

with col2:
    st.metric(
        "✅ Séances",
        f"{completed_sessions}/{total_sessions}",
        f"{int((completed_sessions/total_sessions)*100)}%" if total_sessions > 0 else "0%"
    )

with col3:
    st.metric(
        "📏 Distance",
        f"{completed_distance:.1f} km",
        f"sur {total_distance:.1f} km prévus"
    )

with col4:
    days_remaining = (plan.end_date - today).days
    st.metric(
        "⏰ J-Day",
        f"{days_remaining} jours",
        f"Course le {plan.end_date.strftime('%d/%m/%Y')}"
    )

st.divider()

# ===== GRAPHIQUES =====
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📈 Volume d'entraînement par semaine")
    
    # Préparer les données
    weeks_data = []
    for week in plan.weeks:
        week_distance = sum(s.distance_km for s in week.sessions)
        week_duration = sum(s.duration_minutes for s in week.sessions)
        week_completed = sum(1 for s in week.sessions if s.status == SessionStatus.COMPLETED)
        
        weeks_data.append({
            'Semaine': f"S{week.week_number}",
            'Distance prévue (km)': week_distance,
            'Durée (min)': week_duration,
            'Phase': week.phase.value,
            'Complétées': week_completed,
            'Total': len(week.sessions)
        })
    
    # Graphique barres volume
    fig_volume = go.Figure()
    
    fig_volume.add_trace(go.Bar(
        x=[w['Semaine'] for w in weeks_data],
        y=[w['Distance prévue (km)'] for w in weeks_data],
        name='Distance',
        marker_color='lightblue',
        text=[f"{w['Distance prévue (km)']:.0f} km" for w in weeks_data],
        textposition='outside'
    ))
    
    # Ajouter ligne de phase
    phases = [w['Phase'] for w in weeks_data]
    colors = []
    for phase in phases:
        if 'Base' in phase:
            colors.append('rgba(100, 200, 100, 0.2)')
        elif 'Développement' in phase:
            colors.append('rgba(255, 200, 100, 0.2)')
        else:
            colors.append('rgba(200, 100, 200, 0.2)')
    
    fig_volume.update_layout(
        height=350,
        xaxis_title="Semaine",
        yaxis_title="Distance (km)",
        showlegend=False,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_volume, use_container_width=True)

with col_right:
    st.subheader("🎯 Répartition des types de séances")
    
    # Compter les types de séances
    session_types = {}
    for week in plan.weeks:
        for session in week.sessions:
            session_type = session.session_type.value
            if session_type not in session_types:
                session_types[session_type] = 0
            session_types[session_type] += 1
    
    # Graphique camembert
    fig_pie = go.Figure(data=[go.Pie(
        labels=list(session_types.keys()),
        values=list(session_types.values()),
        hole=0.4,
        marker=dict(
            colors=px.colors.qualitative.Set3
        )
    )])
    
    fig_pie.update_layout(
        height=350,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05
        )
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ===== PROCHAINES SEANCES CLES =====
st.subheader("⭐ Prochaines séances clés")

# Trouver les 3 prochaines séances clés
upcoming_key_sessions = []
for week in plan.weeks:
    for session in week.sessions:
        if session.is_key_session and session.scheduled_date >= today:
            upcoming_key_sessions.append((session, week.week_number))

upcoming_key_sessions.sort(key=lambda x: x[0].scheduled_date)
upcoming_key_sessions = upcoming_key_sessions[:3]

if upcoming_key_sessions:
    cols = st.columns(len(upcoming_key_sessions))
    
    for idx, (session, week_num) in enumerate(upcoming_key_sessions):
        with cols[idx]:
            st.markdown(f"**S{week_num} - {session.scheduled_date.strftime('%d/%m')}**")
            st.info(f"🏃 **{session.title}**\n\n{session.description}\n\n📏 {session.distance_km} km • ⏱️ {session.duration_minutes} min")
else:
    st.info("🎉 Plus de séances clés à venir dans ce plan !")

st.divider()

# ===== DONNEES GARMIN (SI DISPONIBLES) =====
st.subheader("📱 Suivi Garmin (7 derniers jours)")

try:
    garmin = get_garmin_service()
    
    # Récupérer données des 7 derniers jours
    garmin_data = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        try:
            daily = garmin.get_daily_metrics(target_date)
            if daily:
                garmin_data.append({
                    'Date': target_date.strftime('%d/%m'),
                    'Sommeil (h)': daily.sleep.total_sleep_hours if daily.sleep else 0,
                    'Score sommeil': daily.sleep.sleep_score if daily.sleep else 0,
                    'FC repos': daily.rhr.rhr_bpm if daily.rhr else None,
                    'HRV': daily.hrv.hrv_value if daily.hrv else None
                })
        except:
            pass
    
    if garmin_data:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Graphique sommeil
            fig_sleep = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig_sleep.add_trace(
                go.Bar(
                    x=[d['Date'] for d in garmin_data],
                    y=[d['Sommeil (h)'] for d in garmin_data],
                    name='Heures de sommeil',
                    marker_color='lightblue'
                ),
                secondary_y=False
            )
            
            fig_sleep.add_trace(
                go.Scatter(
                    x=[d['Date'] for d in garmin_data],
                    y=[d['Score sommeil'] for d in garmin_data],
                    name='Score',
                    mode='lines+markers',
                    marker=dict(color='orange', size=8),
                    line=dict(color='orange', width=2)
                ),
                secondary_y=True
            )
            
            fig_sleep.update_xaxes(title_text="Date")
            fig_sleep.update_yaxes(title_text="Heures", secondary_y=False)
            fig_sleep.update_yaxes(title_text="Score", secondary_y=True)
            fig_sleep.update_layout(height=300, title_text="😴 Sommeil")
            
            st.plotly_chart(fig_sleep, use_container_width=True)
        
        with col_g2:
            # Graphique FC repos
            fc_data = [d['FC repos'] for d in garmin_data if d['FC repos']]
            if fc_data:
                fig_hr = go.Figure()
                
                fig_hr.add_trace(go.Scatter(
                    x=[d['Date'] for d in garmin_data if d['FC repos']],
                    y=fc_data,
                    mode='lines+markers',
                    marker=dict(color='red', size=10),
                    line=dict(color='red', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(255, 0, 0, 0.1)'
                ))
                
                avg_hr = sum(fc_data) / len(fc_data)
                fig_hr.add_hline(y=avg_hr, line_dash="dash", line_color="gray", 
                                annotation_text=f"Moyenne: {avg_hr:.0f} bpm")
                
                fig_hr.update_layout(
                    height=300,
                    title_text="💓 Fréquence cardiaque au repos",
                    xaxis_title="Date",
                    yaxis_title="FC (bpm)",
                    showlegend=False
                )
                
                st.plotly_chart(fig_hr, use_container_width=True)
            else:
                st.info("Pas de données FC repos disponibles")
        
        # ===== HISTORIQUE DES ACTIVITES =====
        st.divider()
        st.subheader("🏃 Dernières activités Garmin")
        
        try:
            # Récupérer les 5 dernières activités
            activities = garmin.get_recent_activities(limit=5)
            
            if activities:
                for activity in activities:
                    with st.expander(
                        f"📅 {activity['start_time'][:10]} - {activity['activity_type']} • "
                        f"{activity['distance_km']} km • {activity['duration_minutes']} min"
                    ):
                        col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                        
                        with col_a1:
                            st.metric("📏 Distance", f"{activity['distance_km']} km")
                            st.metric("⏱️ Durée", f"{activity['duration_minutes']} min")
                        
                        with col_a2:
                            st.metric("⚡ Allure", activity['pace_str'])
                            if activity['avg_cadence']:
                                st.metric("👟 Cadence", f"{activity['avg_cadence']} spm")
                        
                        with col_a3:
                            if activity['avg_hr']:
                                st.metric("❤️ FC moy", f"{activity['avg_hr']} bpm")
                            if activity['max_hr']:
                                st.metric("💓 FC max", f"{activity['max_hr']} bpm")
                        
                        with col_a4:
                            if activity['calories']:
                                st.metric("🔥 Calories", f"{activity['calories']} kcal")
                            if activity['elevation_gain']:
                                st.metric("⛰️ D+", f"{activity['elevation_gain']} m")
                
                # ===== STATISTIQUES DES ACTIVITES =====
                st.divider()
                st.subheader("📊 Statistiques de vos activités")
                
                # Calculer les stats
                total_dist = sum(a['distance_km'] for a in activities)
                total_time = sum(a['duration_minutes'] for a in activities)
                avg_pace_seconds = sum(a['avg_pace_seconds'] for a in activities if a['avg_pace_seconds']) / len([a for a in activities if a['avg_pace_seconds']])
                avg_pace_min = int(avg_pace_seconds // 60)
                avg_pace_sec = int(avg_pace_seconds % 60)
                
                best_pace = min([a['avg_pace_seconds'] for a in activities if a['avg_pace_seconds']])
                best_pace_min = int(best_pace // 60)
                best_pace_sec = int(best_pace % 60)
                
                longest_dist = max([a['distance_km'] for a in activities])
                
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                
                with col_s1:
                    st.metric(
                        "📏 Distance totale",
                        f"{total_dist:.1f} km",
                        help="Sur les 5 dernières activités"
                    )
                
                with col_s2:
                    st.metric(
                        "⏱️ Temps total",
                        f"{int(total_time/60)}h{int(total_time%60):02d}",
                        help="Sur les 5 dernières activités"
                    )
                
                with col_s3:
                    st.metric(
                        "⚡ Allure moyenne",
                        f"{avg_pace_min}:{avg_pace_sec:02d} /km",
                        help="Moyenne des 5 dernières sorties"
                    )
                
                with col_s4:
                    st.metric(
                        "🏆 Meilleure allure",
                        f"{best_pace_min}:{best_pace_sec:02d} /km",
                        f"Plus longue: {longest_dist:.1f} km"
                    )
                
                # ===== GRAPHIQUE EVOLUTION ALLURE =====
                st.markdown("**Evolution de l'allure**")
                
                fig_pace = go.Figure()
                
                # Inverser l'ordre pour avoir les plus anciennes à gauche
                activities_sorted = sorted(activities, key=lambda x: x['start_time'])
                
                pace_values = []
                dates = []
                for a in activities_sorted:
                    if a['avg_pace_seconds']:
                        pace_values.append(a['avg_pace_seconds'] / 60)  # Convertir en minutes
                        dates.append(a['start_time'][:10])
                
                fig_pace.add_trace(go.Scatter(
                    x=dates,
                    y=pace_values,
                    mode='lines+markers',
                    marker=dict(color='green', size=10),
                    line=dict(color='green', width=2),
                    name='Allure (min/km)'
                ))
                
                fig_pace.update_layout(
                    height=250,
                    xaxis_title="Date",
                    yaxis_title="Allure (min/km)",
                    yaxis=dict(autorange="reversed"),  # Inverser l'axe Y (plus rapide = plus haut)
                    showlegend=False,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_pace, use_container_width=True)
                
            else:
                st.info("Aucune activité récente trouvée sur Garmin")
        
        except Exception as e:
            st.warning(f"Impossible de charger les activités : {str(e)}")
    
    else:
        st.info("📊 Connectez votre compte Garmin dans la page **Today** pour voir les graphiques")

except Exception as e:
    st.info("📊 Activez Garmin dans la page **Today** pour voir vos statistiques physiologiques")

st.divider()

# ===== RESUME DE LA SEMAINE EN COURS =====
current_week_num = None
days_since_start = (today - plan.start_date).days
if 0 <= days_since_start < len(plan.weeks) * 7:
    current_week_num = (days_since_start // 7) + 1

if current_week_num and current_week_num <= len(plan.weeks):
    current_week = plan.weeks[current_week_num - 1]
    
    st.subheader(f"📅 Semaine en cours (S{current_week_num})")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Phase", current_week.phase.value)
        st.metric("Type", current_week.week_type.value)
    
    with col2:
        week_sessions = len(current_week.sessions)
        week_completed = sum(1 for s in current_week.sessions if s.status == SessionStatus.COMPLETED)
        st.metric("Séances", f"{week_completed}/{week_sessions}")
        
        if current_week.focus:
            st.metric("Focus", current_week.focus)
    
    with col3:
        week_distance = sum(s.distance_km for s in current_week.sessions)
        week_duration = sum(s.duration_minutes for s in current_week.sessions)
        st.metric("Distance", f"{week_distance:.1f} km")
        st.metric("Durée", f"{int(week_duration/60)}h{week_duration%60:02d}")
    
    # Calendrier de la semaine
    st.markdown("**Planning de la semaine :**")
    
    
    week_calendar = []
    for session in current_week.sessions:
        jour = get_jour_name(session.day_of_week)
        status_icon = "✅" if session.status == SessionStatus.COMPLETED else "📅"
        week_calendar.append(f"{status_icon} **{jour}** : {session.title} ({session.distance_km} km)")
    
    for item in week_calendar:
        st.markdown(f"- {item}")
