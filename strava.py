import streamlit as st
import urllib.parse
import os
from stravalib.client import Client

# --------------------------
# Configuration OAuth
# --------------------------
CLIENT_ID = "184920"
CLIENT_SECRET = "4823f8d6d840253c058725c460aaf1a5d48cc7bb"
REDIRECT_URI = "http://localhost:8501/"

st.title("Téléchargement des fichiers .FIT Strava (via lien direct)")

# Créer un dossier pour sauvegarder éventuellement les fichiers
os.makedirs("fit_files", exist_ok=True)

# Récupérer le code OAuth
query = st.experimental_get_query_params()
code = query.get("code", [None])[0]

client = Client()

if not code:
    # Générer l'URL d'autorisation Strava
    auth_url = client.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=['read_all', 'activity:read_all'],
        approval_prompt='auto'
    )
    st.markdown(f"[Se connecter à Strava]({auth_url})")
    st.stop()

# Échanger le code OAuth contre un access_token
token_response = client.exchange_code_for_token(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    code=code
)

access_token = token_response['access_token']
client.access_token = access_token

# --------------------------
# Récupérer les dernières activités
# --------------------------
activities = list(client.get_activities(limit=5))  # ici 5 dernières activités

st.subheader("Dernières activités")
for act in activities:
    distance_km = float(act.distance)/1000
    st.write(f"- **{act.name}** — {distance_km:.1f} km")

    # Lien direct pour télécharger le .fit (ouvre dans le navigateur)
    fit_url = f"https://www.strava.com/activities/{act.id}/export_original"
    st.markdown(f"[Télécharger .FIT]({fit_url})")
