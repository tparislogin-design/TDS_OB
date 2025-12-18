import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import config as cfg
import solver

st.set_page_config(page_title="TDS Manager V8.8", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    h1 {color: #1e3a8a;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR : PARAMÈTRES ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/984/984233.png", width=50)
    st.title("Paramètres V8.8")
    
    annee_select = st.number_input("Année", value=cfg.ANNEE)
    
    col_d, col_f = st.columns(2)
    with col_d:
        jour_debut = st.number_input("Jour Début", value=335, min_value=1, max_value=365)
    with col_f:
        jour_fin = st.number_input("Jour Fin", value=348, min_value=1, max_value=365)
        
    st.divider()
    
    st.subheader("Options Avancées")
    timeout = st.slider("Temps calcul max (s)", 5, 60, cfg.SOLVER_TIME_LIMIT)
    cfg.SOLVER_TIME_LIMIT = timeout # Mise à jour dynamique
    
    buffer_days = st.number_input("Buffer Jours", value=cfg.BUFFER_DAYS)
    cfg.BUFFER_DAYS = buffer_days

# --- CORPS PRINCIPAL ---
st.title(f"✈️ Planification ATC - Année {annee_select}")
st.markdown(f"**Période :** J{jour_debut} à J{jour_fin} | **Contrôleurs :** {len(cfg.CONTROLEURS)}")

# Bouton d'action
if st.button("🚀 LANCER L'OPTIMISATION (Moteur V8.8)", type="primary", use_container_width=True):
    
    with st.spinner("Initialisation du solveur OR-Tools... Intégration des contraintes GAO/LAK..."):
        # Simulation chargement GSheet (à remplacer par le vrai appel si tu as les secrets)
        # pre_assignments = load_gsheet(...) 
        pre_assignments = {} # Vide pour l'instant
        
        # Appel du fichier solver.py
        df_result, status = solver.run_solver(jour_debut, jour_fin, annee_select, pre_assignments)
        
        if df_result is not None:
            st.success(f"Optimisation terminée : {status}")
            st.session_state['df_planning'] = df_result
        else:
            st.error("Impossible de trouver une solution avec ces contraintes (Infaisable).")

# --- AFFICHAGE RÉSULTAT ---
if 'df_planning' in st.session_state:
    df = st.session_state['df_planning']
    
    # Préparation AgGrid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("Agent", pinned="left", width=120, cellStyle={'fontWeight': 'bold'})
    
    # Javascript pour les couleurs (reprise de ton code)
    cells_js = JsCode("""
    function(params) {
        if (params.value == 'M') return {'backgroundColor': '#ffeebb', 'color': 'black', 'textAlign': 'center', 'fontWeight': 'bold'};
        if (params.value == 'J1' || params.value == 'J2') return {'backgroundColor': '#d4edda', 'color': 'black', 'textAlign': 'center'};
        if (params.value == 'A1' || params.value == 'A2') return {'backgroundColor': '#cce5ff', 'color': 'black', 'textAlign': 'center'};
        if (params.value == 'S') return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'textAlign': 'center', 'fontWeight': 'bold'};
        if (params.value == 'OFF') return {'backgroundColor': '#f0f2f6', 'color': '#ccc', 'textAlign': 'center'};
        return {'textAlign': 'center'};
    }
    """)

    # Configurer les colonnes de jours
    cols_jours = [c for c in df.columns if c != 'Agent']
    for col in cols_jours:
        # Essayer de formater la date en entête
        dt = solver.get_datetime_from_day_num(annee_select, int(col))
        label = f"{dt.strftime('%d/%m')} (J{col})" if dt else str(col)
        
        gb.configure_column(col, headerName=label, width=85, cellStyle=cells_js, editable=True)

    gb.configure_grid_options(rowHeight=40)
    gridOptions = gb.build()
    
    st.subheader("Planning Généré")
    AgGrid(df, gridOptions=gridOptions, allow_unsafe_jscode=True, height=600, theme="alpine")
    
    # Export
    st.download_button("Télécharger en CSV", df.to_csv().encode('utf-8'), "planning_atc.csv")
