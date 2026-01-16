import streamlit as st

st.set_page_config(
    page_title="Coach Semi-Marathon Sub 1:45",
    page_icon="🏃",
    layout="wide"
)

st.title("🏃 Coach Semi-Marathon Sub 1:45")
st.subheader("Votre entraîneur intelligent personnalisé")

st.markdown("""
## Bienvenue ! 👋

Ce coach d'entraînement intelligent vous aide à atteindre votre objectif de **semi-marathon en moins de 1h45** (rythme 4:58/km).

### 🎯 Fonctionnalités

- **📅 Plan d'entraînement** : Plan personnalisé de 12 semaines avec 3 phases (Base, Build, Taper)
- **🎯 Recommandation du jour** : Analyse quotidienne de votre récupération et adaptation automatique de vos séances
- **📊 Dashboard** : Suivi de votre progression et statistiques
- **⚙️ Paramètres** : Configuration de votre profil et connexion aux APIs

### 🚀 Commencer

👉 **Rendez-vous sur la page "Today"** pour obtenir votre recommandation du jour !

---

### 📖 Comment ça marche ?

1. **Chaque matin** : L'app analyse votre sommeil, fatigue, et charge d'entraînement
2. **Recommandation** : Le coach adapte automatiquement votre séance du jour
3. **Flexibilité** : Vos séances sont ajustées selon votre disponibilité et récupération
4. **Objectif** : Progression régulière vers le sub 1:45 sans blessure

### 🎯 Votre objectif

- **Distance** : Semi-Marathon (21.1 km)
- **Temps cible** : < 1:45:00
- **Rythme** : 4:58 /km
- **VMA recommandée** : 17 km/h

---

### 🔜 Prochaines fonctionnalités

- 🔗 Connexion Garmin (activités, sommeil, fréquence cardiaque)
- 📅 Intégration Google Calendar
- 🤖 Suggestions IA avec Mistral
- 📊 Graphiques de progression
""")

# Quick stats mockup
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Semaine actuelle", "1 / 12")

with col2:
    st.metric("Séances complétées", "0 / 48")

with col3:
    st.metric("Distance parcourue", "0 km")

with col4:
    st.metric("Score récupération", "N/A")

st.info("💡 **Astuce** : Utilisez la barre latérale pour naviguer entre les pages")
