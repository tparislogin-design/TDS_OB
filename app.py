import streamlit as st
import pandas as pd
import random

# Configuration de la page
st.set_page_config(page_title="ATC Planner - Tour de Contrôle", layout="wide")

st.title("✈️ ATC Planner - Prototype")

# 1. BARRE LATÉRALE : Paramètres de simulation
with st.sidebar:
    st.header("Paramètres du Service")
    nb_controleurs = st.slider("Nombre de contrôleurs présents", 3, 10, 5)
    heure_debut = st.time_input("Début de service", value=pd.to_datetime("07:00").time())
    heure_fin = st.time_input("Fin de service", value=pd.to_datetime("14:00").time())
    
    st.subheader("Contraintes")
    pause_min = st.checkbox("Respecter pause 33%", value=True)
    qualification = st.multiselect("Postes ouverts", ["SOL", "LOC (Tour)", "APP (Approche)", "PREVOL"], default=["SOL", "LOC (Tour)"])

    if st.button("Générer le Planning"):
        st.success("Calcul en cours...")
        # Ici, on appellerait le vrai moteur OR-Tools plus tard
        st.session_state['generated'] = True

# 2. ZONE PRINCIPALE : Visualisation
st.subheader("Visualisation du Planning (Vue Grille)")

# Simulation de données pour l'exemple (MOCK DATA)
# Pour tester le frontend, on n'a pas besoin du vrai algo, on fait du "faux" intelligent
def generate_mock_data(nb_agents, postes_dispo):
    creneaux = [f"{h:02d}:00 - {h+1:02d}:00" for h in range(7, 14)]
    agents = [f"Ctlr_{i+1}" for i in range(nb_agents)]
    
    data = {}
    for agent in agents:
        planning_jour = []
        for _ in creneaux:
            # Assigne un poste ou une pause au hasard pour l'exemple visuel
            etat = random.choice(postes_dispo + ["PAUSE", "PAUSE"]) 
            planning_jour.append(etat)
        data[agent] = planning_jour
        
    return pd.DataFrame(data, index=creneaux)

# Affichage du tableau si le bouton a été cliqué ou par défaut
df_planning = generate_mock_data(nb_controleurs, qualification)

# Astuce visuelle : On colore les cellules pour voir les pauses et les postes
def color_planning(val):
    color = 'white'
    if val == 'PAUSE':
        color = '#ffcccb' # Rouge clair
    elif val == 'LOC (Tour)':
        color = '#add8e6' # Bleu clair
    elif val == 'SOL':
        color = '#90ee90' # Vert clair
    return f'background-color: {color}; color: black; border: 1px solid grey'

# Affichage interactif
st.dataframe(df_planning.style.map(color_planning), use_container_width=True, height=400)

# 3. STATISTIQUES (KPIs)
col1, col2, col3 = st.columns(3)
col1.metric("Positions Ouvertes Simult.", len(qualification))
col2.metric("Taux d'occupation", "85%")
col3.metric("Infractions Détectées", "0", delta_color="normal")

st.info("Ceci est une maquette visuelle. L'intelligence artificielle (OR-Tools) sera connectée à ce tableau pour remplacer le hasard.")