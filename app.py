import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configuration large pour ressembler à l'écran TDS
st.set_page_config(page_title="TDS Manager - IA", layout="wide")

# --- CSS PERSONNALISÉ (Pour imiter le style "Pro") ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h1 {font-size: 1.5rem; margin-bottom: 0;}
    div[data-testid="stMetricValue"] {font-size: 1.2rem;}
    </style>
""", unsafe_allow_html=True)

# Titre et Menu comme sur ton image
col_titre, col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([4, 1, 1, 1, 1])
with col_titre:
    st.title("✈️ TDS Manager (Moteur IA)")
with col_btn1:
    st.button("📅 Planning", use_container_width=True, type="primary")
with col_btn2:
    st.button("⚙️ Config", use_container_width=True)
with col_btn3:
    st.button("📋 Désidérata", use_container_width=True)
with col_btn4:
    st.button("📊 Bilan", use_container_width=True)

st.divider()

# --- 1. PARAMÈTRES (Barre du haut sur ton image) ---
c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
with c1:
    mois_select = st.selectbox("Période", ["Janvier 2026", "Février 2026"])
with c2:
    st.info("⚠️ 2 Violations détectées") # Fake pour l'exemple
with c3:
    zoom = st.slider("Zoom", 50, 150, 100, label_visibility="collapsed")
with c4:
    st.download_button("⬇️ Export Excel", "data", file_name="planning.xlsx", use_container_width=True)

# --- 2. DONNÉES SIMULÉES (Pour reproduire la structure) ---
agents = ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN", "TRT", "CLO"]
jours = [f"{i}/01" for i in range(1, 15)] # 14 premiers jours
jours_semaine = ["LU", "MA", "ME", "JE", "VE", "SA", "DI"] * 2

# Création d'une structure vide
data = { "CONTRÔLEUR": [f"{a} (0/12)" for a in agents] }

# Remplissage aléatoire pour l'effet visuel (Simule le résultat de l'IA)
codes_possibles = ["M", "J1", "J2", "J3", "A1", "S", "", ""] # "" = Repos
for i, jour in enumerate(jours):
    nom_col = f"{jours_semaine[i]} {jour}"
    col_valeurs = []
    for _ in agents:
        val = np.random.choice(codes_possibles)
        col_valeurs.append(val)
    data[nom_col] = col_valeurs

df = pd.DataFrame(data)
df.set_index("CONTRÔLEUR", inplace=True)

# --- 3. AFFICHAGE STYLE (Couleurs comme sur ton image) ---
def color_sur_tours(val):
    color = 'white'
    font_weight = 'normal'
    
    if val == 'M': 
        color = '#ffeba0' # Jaune
        font_weight = 'bold'
    elif val in ['J1', 'J2', 'J3']: 
        color = '#d4edda' # Vert pâle
    elif val in ['A1', 'A2']: 
        color = '#cce5ff' # Bleu pâle
    elif val == 'S': 
        color = '#f8d7da' # Rouge pâle
        
    return f'background-color: {color}; color: black; font-weight: {font_weight}; text-align: center; border: 1px solid #eee'

# Affichage de la grille principale
st.subheader("Grille Principale")
st.dataframe(df.style.map(color_sur_tours), height=500, use_container_width=True)

# Note de bas de page
st.caption("Clic Gauche : Verrouiller | Clic Droit : Refuser (Fonctionnalités à venir avec AgGrid)")
