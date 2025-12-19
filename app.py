import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import solver

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="TDS Manager", layout="wide", initial_sidebar_state="collapsed")

# --- 2. CSS "PIXEL PERFECT" (Pour imiter ta capture) ---
st.markdown("""
<style>
    /* Reset général pour maximiser l'espace */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100% !important;
    }
    
    /* Cacher les éléments Streamlit par défaut */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;} /* Cache la barre colorée du haut */

    /* --- STYLE DU HEADER PERSONNALISÉ --- */
    .custom-header {
        background-color: #ffffff;
        border-bottom: 1px solid #e0e0e0;
        padding: 10px 20px;
        display: flex;
        align-items: center;
        justify_content: space-between;
        margin-bottom: 15px;
    }
    .header-title {
        font-family: 'Segoe UI', sans-serif;
        font-size: 1.2rem;
        font-weight: 700;
        color: #1f1f1f;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-icon {
        background-color: #2563eb;
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
    .nav-buttons {
        display: flex;
        gap: 5px;
        background-color: #f3f4f6;
        padding: 4px;
        border-radius: 6px;
    }
    .nav-btn {
        background: none;
        border: none;
        padding: 6px 15px;
        font-size: 0.9rem;
        font-weight: 500;
        color: #4b5563;
        cursor: pointer;
        border-radius: 4px;
    }
    .nav-btn.active {
        background-color: white;
        color: #2563eb;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        font-weight: 600;
    }

    /* --- STYLE DES PANNEAUX (DROITE) --- */
    .right-panel-card {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .panel-header {
        font-size: 0.85rem;
        font-weight: 700;
        color: #374151;
        text-transform: uppercase;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* --- BOUTONS STYLISÉS --- */
    .stButton > button {
        border-radius: 4px;
        font-size: 0.9rem;
        font-weight: 600;
        border: none;
    }
    /* Bouton vert (Import) */
    div[data-testid="stVerticalBlock"] > div > div > div > div > button {
         /* Astuce: On cible les boutons génériques, ajustement fin nécessaire selon contexte */
    }

    /* --- AG GRID HEADERS --- */
    /* Pour permettre le texte sur plusieurs lignes dans les en-têtes */
    .ag-header-cell-label .ag-header-cell-text {
        white-space: pre-wrap !important;
        text-align: center;
        font-size: 0.75rem;
        line-height: 1.1;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. FONCTIONS UTILITAIRES ---
def get_day_info(year, day_num):
    """Retourne (NomJour, Date) ex: ('LU', '31/12')"""
    try:
        dt = datetime(year, 1, 1) + timedelta(days=day_num - 1)
        # Jours en français (approximatif pour l'exemple)
        jours = ["LU", "MA", "ME", "JE", "VE", "SA", "DI"]
        return jours[dt.weekday()], dt.strftime("%d/%m")
    except:
        return "ERR", "00/00"

def load_config():
    if os.path.exists("config.json"):
        with open("config.json", 'r') as f: return json.load(f)
    return {"ANNEE": 2026, "CONTROLEURS": ["GAO", "WBR"], "CONTRAT": {}}

# --- 4. HEADER PERSONNALISÉ (HTML) ---
# On recrée la barre du haut de ta capture
st.markdown("""
<div class="custom-header">
    <div class="header-title">
        <div class="header-icon">✝</div>
        TDS Manager <span style="font-size:0.8rem; color:#22c55e; margin-left:5px;">● Fichier: Désidérata</span>
    </div>
    <div class="nav-buttons">
        <button class="nav-btn active">📅 Planning</button>
        <button class="nav-btn">⚙ Configuration</button>
        <button class="nav-btn">📋 Désidérata</button>
        <button class="nav-btn">📊 Bilan</button>
    </div>
    <div style="width: 150px;">
        <!-- Espace réservé pour le bouton Streamlit natif à droite -->
    </div>
</div>
""", unsafe_allow_html=True)

# --- 5. LAYOUT PRINCIPAL (75% Gauche / 25% Droite) ---
col_main, col_right = st.columns([78, 22], gap="medium")

# Chargement config
if 'config' not in st.session_state: st.session_state['config'] = load_config()
config = st.session_state['config']

# =========================================================
# COLONNE DE DROITE (PARAMÈTRES & CSV)
# =========================================================
with col_right:
    # --- CARTE 1 : IMPORT CSV ---
    with st.container():
        st.markdown('<div class="right-panel-card">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">📗 SOURCE CSV (LECTURE)</div>', unsafe_allow_html=True)
        st.text_input("URL Google Sheet (Public)", value="https://docs.google.com...", disabled=True, label_visibility="collapsed")
        st.caption("Nom de la feuille: Désidérata")
        
        if st.button("📥 Importer Désidérata", use_container_width=True, type="secondary"):
            st.toast("Données importées !", icon="✅")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- CARTE 2 : PARAMÈTRES GÉNÉRAUX ---
    with st.container():
        st.markdown('<div class="right-panel-card">', unsafe_allow_html=True)
        st.markdown('<div class="panel-header">⚙ PARAMÈTRES GÉNÉRAUX</div>', unsafe_allow_html=True)
        
        # Inputs compacts comme sur la capture
        c_annee = st.number_input("Année", value=config.get("ANNEE", 2026), label_visibility="visible")
        c1, c2 = st.columns(2)
        with c1: jd = st.number_input("Jour Début", value=365)
        with c2: jf = st.number_input("Jour Fin", value=28)
        
        st.markdown("---")
        st.write("**Temps Limite** (s) : **25**")
        st.slider("Temps", 5, 60, 25, label_visibility="collapsed")
        
        st.number_input("Max Heures (7j glissants)", value=44)
        st.number_input("Repos Min", value=11)
        st.number_input("Max Consécutifs", value=4)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Bouton Lancer Optimisation (Bleu, en haut à droite normalement, ici en bas de colonne pour l'exemple)
    st.button("⚡ Lancer Optimisation", type="primary", use_container_width=True)

# =========================================================
# COLONNE PRINCIPALE (GRILLE PLANNING)
# =========================================================
with col_main:
    # --- BARRE D'OUTILS ---
    tb_col1, tb_col2, tb_col3, tb_col4 = st.columns([2, 2, 4, 2])
    with tb_col1:
        st.button("👁 Voir Sources", use_container_width=True)
    with tb_col2:
        st.button("⚠ Voir Violations", use_container_width=True)
    with tb_col3:
        # Contrôle du Zoom (Fake slider visuel)
        st.slider("Zoom", 50, 150, 100, label_visibility="collapsed")
    with tb_col4:
        st.button("⬇ Export Excel", use_container_width=True)

    # --- PRÉPARATION DES DONNÉES DE LA GRILLE ---
    # Génération d'un DataFrame vide qui ressemble à ta capture
    if 'df_planning' not in st.session_state:
        agents = config["CONTROLEURS"]
        # Création des colonnes pour la période (Exemple capture: 365 -> 26)
        # Simplification : On génère 15 jours
        cols = []
        headers_def = {}
        
        # Logique pour créer les en-têtes sur 3 lignes (Jour, Numéro, Date)
        start_day = 365
        year = config.get("ANNEE", 2026)
        
        days_to_show = []
        # Fin d'année 2025
        days_to_show.append((year-1, 365))
        # Début année 2026
        for i in range(1, 16): days_to_show.append((year, i))
            
        for y, d in days_to_show:
            nom_jour, date_jour = get_day_info(y, d)
            col_id = f"{d}" # ID unique
            # Formatage spécial pour le header AgGrid: "LU\n365\n31/12"
            header_label = f"{nom_jour}\n{d}\n{date_jour}"
            cols.append(col_id)
            headers_def[col_id] = header_label

        # Création du DF
        data = []
        for agent in agents:
            row = {"Agent": f"{agent}\n0 / 12"} # Ajout des stats sous le nom
            for c in cols:
                row[c] = "" # Vide par défaut
            data.append(row)
        
        st.session_state['df_planning'] = pd.DataFrame(data)
        st.session_state['headers_def'] = headers_def

    df = st.session_state['df_planning']
    headers_mapping = st.session_state['headers_def']

    # --- CONFIGURATION AG-GRID ---
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # 1. Colonne Agent (Style spécifique avec saut de ligne)
    gb.configure_column("Agent", pinned="left", width=80, cellStyle={
        'fontWeight': 'bold', 
        'backgroundColor': '#f8fafc', 
        'whiteSpace': 'pre-wrap', # Permet le saut de ligne pour "GAO \n 0/12"
        'fontSize': '0.8rem',
        'lineHeight': '1.2',
        'display': 'flex',
        'alignItems': 'center'
    })

    # 2. Colonnes Jours
    # Rendu JS conditionnel (Couleurs)
    js_renderer = JsCode("""
    function(params) {
        if (!params.value) return {'textAlign': 'center', 'borderRight': '1px solid #eee'};
        const colors = {
            'M': '#fff7ed', 'J1': '#f0fdf4', 'J2': '#dcfce7', 
            'J3': '#bbf7d0', 'A1': '#eff6ff', 'A2': '#dbeafe', 'S': '#fef2f2'
        };
        const txtColors = {
            'M': '#c2410c', 'J1': '#15803d', 'J2': '#166534', 
            'J3': '#14532d', 'A1': '#1d4ed8', 'A2': '#1e40af', 'S': '#b91c1c'
        };
        return {
            'backgroundColor': col
