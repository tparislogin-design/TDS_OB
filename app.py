import streamlit as st
import pandas as pd
import json
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import solver

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="TDS Manager Pro", layout="wide")

# --- GESTION CONFIGURATION (JSON) ---
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

# Chargement initial
if 'config' not in st.session_state:
    st.session_state['config'] = load_config()

config = st.session_state['config']

# --- CSS PRO ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    h1 {color: #0f172a; font-family: 'Helvetica Neue', sans-serif;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #f1f5f9; border-radius: 5px;
        color: #64748b; font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: #ffffff; color: #2563eb; border-top: 2px solid #2563eb;}
</style>
""", unsafe_allow_html=True)

st.title("✈️ TDS Manager Pro")

# --- NAVIGATION ---
tab_planning, tab_config = st.tabs(["📅 PLANNING OPÉRATIONNEL", "⚙️ CONFIGURATION"])

# =========================================================
# ONGLET 1 : PLANNING (Le moteur)
# =========================================================
with tab_planning:
    # Barre de contrôle
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    with c1:
        annee_select = st.number_input("Année", value=config["ANNEE"])
    with c2:
        jour_debut = st.number_input("Début (J)", value=335, min_value=1, max_value=365)
    with c3:
        jour_fin = st.number_input("Fin (J)", value=348, min_value=1, max_value=365)
    with c4:
        st.write("") # Spacer
        st.write("") 
        if st.button("⚡ CALCULER LE PLANNING", type="primary", use_container_width=True):
            with st.spinner("Optimisation mathématique en cours..."):
                df_result, status = solver.run_solver(
                    jour_debut, jour_fin, annee_select, config, {}
                )
                if df_result is not None:
                    st.success(f"Résultat : {status}")
                    st.session_state['df_planning'] = df_result
                else:
                    st.error("Impossible de trouver une solution.")

    # Affichage Grille
    if 'df_planning' in st.session_state:
        df = st.session_state['df_planning'].copy()
        df.columns = df.columns.astype(str) # Fix pour AgGrid
        
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_column("Agent", pinned="left", width=100, cellStyle={'fontWeight': 'bold', 'backgroundColor': '#f8fafc'})
        
        # Style conditionnel (Code JS)
        js_cell_style = JsCode("""
        function(params) {
            if (params.value == 'M')  return {'backgroundColor': '#fff7ed', 'color': '#9a3412', 'fontWeight': 'bold', 'textAlign': 'center'};
            if (params.value == 'J1') return {'backgroundColor': '#f0fdf4', 'color': '#166534', 'fontWeight': 'bold', 'textAlign': 'center'};
            if (params.value == 'J2') return {'backgroundColor': '#dcfce7', 'color': '#14532d', 'fontWeight': 'bold', 'textAlign': 'center'};
            if (params.value == 'J3') return {'backgroundColor': '#bbf7d0', 'color': '#052e16', 'fontWeight': 'bold', 'textAlign': 'center'};
            if (params.value == 'A1') return {'backgroundColor': '#eff6ff', 'color': '#1e40af', 'fontWeight': 'bold', 'textAlign': 'center'};
            if (params.value == 'A2') return {'backgroundColor': '#dbeafe', 'color': '#1e3a8a', 'fontWeight': 'bold', 'textAlign': 'center'};
            if (params.value == 'S')  return {'backgroundColor': '#fef2f2', 'color': '#991b1b', 'fontWeight': 'bold', 'textAlign': 'center'};
            if (params.value == 'OFF') return {'backgroundColor': '#ffffff', 'color': '#cbd5e1', 'textAlign': 'center', 'fontSize': '0.8em'};
            if (params.value == 'C')   return {'backgroundColor': '#f1f5f9', 'color': '#64748b', 'textAlign': 'center', 'fontStyle': 'italic'};
            return {'textAlign': 'center'};
        }
        """)

        cols_jours = [c for c in df.columns if c != 'Agent']
        for col in cols_jours:
            gb.configure_column(col, width=65, cellStyle=js_cell_style, editable=True)

        gb.configure_grid_options(rowHeight=35)
        AgGrid(df, gridOptions=gb.build(), allow_unsafe_jscode=True, height=500, theme="balham")

# =========================================================
# ONGLET 2 : CONFIGURATION (L'éditeur)
# =========================================================
with tab_config:
    st.info("💡 Modifiez ici les règles du jeu. Sauvegardez pour appliquer au prochain calcul.")
    
    col_gauche, col_droite = st.columns([1, 2])
    
    # --- 1. ÉQUIPE (GAUCHE) ---
    with col_gauche:
        st.subheader("👥 Équipe")
        
        # Gestion des Contrôleurs (Liste texte simple)
        current_agents = config.get("CONTROLEURS", [])
        agents_str = st.text_area(
            "Liste des Contrôleurs (un par ligne)", 
            value="\n".join(current_agents),
            height=300
        )
        # Gestion du Bureau
        bureau_agents = st.multiselect(
            "Agents hors-tour (Bureau/Chef)",
            options=agents_str.split("\n"),
            default=config.get("CONTROLLERS_AFFECTES_BUREAU", [])
        )

    # --- 2. RÈGLES & VACATIONS (DROITE) ---
    with col_droite:
        st.subheader("⚙️ Paramètres Moteur")
        
        # Paramètres numériques
        c1, c2, c3 = st.columns(3)
        with c1:
            max_cons = st.number_input("Max Consécutifs", value=config["CONTRAT"]["MAX_CONSECUTIVE_SHIFTS"])
        with c2:
            min_rest = st.number_input("Repos Min (Heures)", value=config["CONTRAT"]["MIN_REST_HOURS"])
        with c3:
            time_limit = st.number_input("Temps Calcul (s)", value=config["CONTRAT"]["SOLVER_TIME_LIMIT"])

        st.divider()
        st.subheader("🕒 Définition des Vacations")
        
        # Éditeur de Vacations (Tableau interactif)
        # On transforme le dict JSON en DataFrame pour l'éditeur
        vacs_data = []
        for code, horaires in config["VACATIONS"].items():
            vacs_data.append({"Code": code, "Début": horaires["debut"], "Fin": horaires["fin"]})
        
        df_vacs = pd.DataFrame(vacs_data)
        
        edited_vacs = st.data_editor(
            df_vacs, 
            num_rows="dynamic", # Permet d'ajouter des lignes !
            use_container_width=True,
            column_config={
                "Début": st.column_config.NumberColumn("Début (h)", format="%.1f"),
                "Fin": st.column_config.NumberColumn("Fin (h)", format="%.1f")
            }
        )

    # --- BOUTON DE SAUVEGARDE GLOBAL ---
    st.write("---")
    if st.button("💾 SAUVEGARDER LA CONFIGURATION", type="primary"):
        # 1. Reconstruire la liste des agents
        new_agents = [a.strip() for a in agents_str.split("\n") if a.strip()]
        
        # 2. Reconstruire le dictionnaire des vacations depuis le tableau
        new_vacations = {}
        for index, row in edited_vacs.iterrows():
            if row["Code"]: # Ignorer les lignes vides
                new_vacations[row["Code"]] = {"debut": float(row["Début"]), "fin": float(row["Fin"])}
        
        # 3. Mise à jour de l'objet config
        new_config = config.copy()
        new_config["CONTROLEURS"] = new_agents
        new_config["CONTROLLERS_AFFECTES_BUREAU"] = bureau_agents
        new_config["VACATIONS"] = new_vacations
        new_config["CONTRAT"]["MAX_CONSECUTIVE_SHIFTS"] = max_cons
        new_config["CONTRAT"]["MIN_REST_HOURS"] = min_rest
        new_config["CONTRAT"]["SOLVER_TIME_LIMIT"] = time_limit
        
        # 4. Sauvegarde disque et session
        save_config(new_config)
        st.session_state['config'] = new_config
        st.toast("Configuration sauvegardée avec succès !", icon="✅")
        st.rerun()
