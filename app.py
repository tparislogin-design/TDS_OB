import streamlit as st
import pandas as pd
import json
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import solver

# --- 1. CONFIGURATION DE LA PAGE (Look "Application Web") ---
st.set_page_config(page_title="TDS Manager", layout="wide", initial_sidebar_state="collapsed")

# Injecter du CSS pour masquer le style "Streamlit" par défaut et faire "App Pro"
st.markdown("""
<style>
    /* Supprimer les marges énormes de Streamlit */
    .block-container {padding-top: 1rem; padding-bottom: 1rem; max-width: 98% !important;}
    
    /* Cacher le menu hamburger et le footer pour un look "SaaS" */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Style des onglets */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px; white-space: pre-wrap; background-color: #f1f5f9; border-radius: 6px;
        color: #475569; font-weight: 600; font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] { background-color: #ffffff; color: #2563eb; border-top: 3px solid #2563eb; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);}
    
    /* Titres */
    h1 { font-family: 'Inter', sans-serif; font-weight: 700; color: #0f172a; font-size: 1.8rem; }
    
    /* Boutons */
    div.stButton > button { border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTION DE LA CONFIGURATION (JSON) ---
CONFIG_FILE = "config.json"

def load_config():
    # Configuration par défaut si le fichier n'existe pas
    default_config = {
        "ANNEE": 2025,
        "CONTROLEURS": ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN"],
        "CONTROLLERS_AFFECTES_BUREAU": [],
        "VACATIONS": {"M": {"debut": 6.0, "fin": 14.0}, "S": {"debut": 15.0, "fin": 23.0}},
        "CONTRAT": {"MIN_REST_HOURS": 11, "MAX_CONSECUTIVE_SHIFTS": 4, "BUFFER_DAYS": 4, "SOLVER_TIME_LIMIT": 10}
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return default_config

def save_config(config_data):
    # Note: Sur Streamlit Cloud, ceci ne persiste pas après reboot
    # Mais c'est suffisant pour la session active.
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

if 'config' not in st.session_state:
    st.session_state['config'] = load_config()

config = st.session_state['config']

# --- 3. JAVASCRIPT PUR (Pour le Rendu Frontend) ---
# C'est ici que tu obtiens ton rendu "React" fluide.
# Ce code est exécuté par le navigateur, pas par Python.
RENDERER_JS = JsCode("""
function(params) {
    if (!params.value) return {'textAlign': 'center'};

    // Palette de couleurs "Modern UI"
    const colors = {
        'M':  {bg: '#fff7ed', text: '#9a3412', border: '#ffedd5'}, // Orange
        'J1': {bg: '#f0fdf4', text: '#166534', border: '#dcfce7'}, // Vert
        'J2': {bg: '#dcfce7', text: '#14532d', border: '#bbf7d0'}, // Vert Foncé
        'J3': {bg: '#bbf7d0', text: '#052e16', border: '#86efac'}, // Vert Arbre
        'A1': {bg: '#eff6ff', text: '#1e40af', border: '#dbeafe'}, // Bleu
        'A2': {bg: '#dbeafe', text: '#1e3a8a', border: '#bfdbfe'}, // Bleu Roi
        'S':  {bg: '#fef2f2', text: '#991b1b', border: '#fee2e2'}, // Rouge
        'OFF':{bg: '#f8fafc', text: '#94a3b8', border: '#e2e8f0'}, // Gris
        'C':  {bg: '#f1f5f9', text: '#64748b', border: '#e2e8f0'}  // Gris Foncé
    };

    const style = colors[params.value] || {bg: 'white', text: 'black', border: '#eee'};

    return {
        'backgroundColor': style.bg,
        'color': style.text,
        'fontWeight': 'bold',
        'textAlign': 'center',
        'borderRight': '1px solid ' + style.border, // Séparateur vertical subtil
        'borderRadius': '0px' // Look Excel
    };
}
""")

# --- 4. INTERFACE UTILISATEUR ---

st.title("✈️ TDS Manager")

# Onglets principaux
tab_planning, tab_config = st.tabs(["📅 PLANNING & OPÉRATIONS", "⚙️ CONFIGURATION & RÈGLES"])

# =========================================================
# ONGLET 1 : LE PLANNING (Moteur + Visuel JS)
# =========================================================
with tab_planning:
    # Barre d'outils compacte
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    with col1: annee = st.number_input("Année", value=config["ANNEE"], label_visibility="collapsed")
    with col2: j_debut = st.number_input("J. Début", value=335, label_visibility="collapsed")
    with col3: j_fin = st.number_input("J. Fin", value=348, label_visibility="collapsed")
    with col4: st.write("") # Spacer
    with col5:
        if st.button("⚡ CALCULER LE PLANNING", type="primary", use_container_width=True):
            with st.spinner("Optimisation en cours (OR-Tools)..."):
                # Simulation données externes (vide pour l'instant)
                res, status = solver.run_solver(j_debut, j_fin, annee, config, {})
                if res is not None:
                    st.toast(f"Calcul terminé : {status}", icon="✅")
                    st.session_state['df_planning'] = res
                else:
                    st.error("Aucune solution trouvée.")

    st.divider()

    # Affichage Grille "Pixel Perfect"
    if 'df_planning' in st.session_state:
        df = st.session_state['df_planning'].copy()
        
        # ⚠️ CRITIQUE : Conversion des noms de colonnes en String pour le JS
        df.columns = df.columns.astype(str)

        # Construction de la grille
        gb = GridOptionsBuilder.from_dataframe(df)
        
        # Colonne Agent figée
        gb.configure_column("Agent", pinned="left", width=90, cellStyle={'fontWeight': 'bold', 'backgroundColor': '#ffffff', 'color': '#334155', 'borderRight': '2px solid #e2e8f0'})

        # Colonnes Jours (Boucle dynamique)
        cols_jours = [c for c in df.columns if c != 'Agent']
        for col in cols_jours:
            # Formatage intelligent de l'en-tête (ex: "Lu 01")
            header_name = col
            is_we = False
            try:
                d_num = int(col)
                dt = solver.get_datetime_from_day_num(annee, d_num)
                if dt:
                    header_name = f"{dt.strftime('%a')[:2]}. {dt.day:02d}"
                    if dt.isoweekday() >= 6: is_we = True
            except: pass

            gb.configure_column(
                col,
                headerName=header_name,
                width=60,
                cellStyle=RENDERER_JS, # Application du JS ici
                editable=True,
                cellClass="weekend-col" if is_we else ""
            )

        # Options Globales Grid
        gb.configure_grid_options(
            rowHeight=32, # Très compact
            headerHeight=35,
            suppressMovableColumns=True,
            enableCellChangeFlash=True # Petit flash quand on édite
        )

        gridOptions = gb.build()

        AgGrid(
            df,
            gridOptions=gridOptions,
            allow_unsafe_jscode=True, # Indispensable pour notre JS
            height=600,
            theme="balham", # Thème Pro compact
            width='100%'
        )
    else:
        st.info("👋 Cliquez sur 'CALCULER' pour générer une première grille.")

# =========================================================
# ONGLET 2 : CONFIGURATION (Low Code)
# =========================================================
with tab_config:
    c_left, c_right = st.columns([1, 2])
    
    with c_left:
        st.subheader("👥 Agents")
        agents_txt = st.text_area("Liste (1/ligne)", value="\n".join(config["CONTROLEURS"]), height=250)
        
    with c_right:
        st.subheader("⚙️ Paramètres & Vacations")
        
        # Paramètres Contrat
        cc1, cc2 = st.columns(2)
        with cc1:
            max_cons = st.number_input("Max Consécutifs", value=config["CONTRAT"]["MAX_CONSECUTIVE_SHIFTS"])
        with cc2:
            min_rest = st.number_input("Repos Min (h)", value=config["CONTRAT"]["MIN_REST_HOURS"])
            
        # Éditeur de Vacations
        vacs_list = [{"Code": k, "Début": v["debut"], "Fin": v["fin"]} for k,v in config["VACATIONS"].items()]
        df_vacs = pd.DataFrame(vacs_list)
        edited_vacs = st.data_editor(df_vacs, num_rows="dynamic", use_container_width=True)

    st.write("---")
    if st.button("💾 SAUVEGARDER CONFIGURATION", type="secondary"):
        # Reconstitution de l'objet Config
        new_conf = config.copy()
        new_conf["CONTROLEURS"] = [x.strip() for x in agents_txt.split('\n') if x.strip()]
        new_conf["CONTRAT"]["MAX_CONSECUTIVE_SHIFTS"] = max_cons
        new_conf["CONTRAT"]["MIN_REST_HOURS"] = min_rest
        
        new_vacs_dict = {}
        for _, row in edited_vacs.iterrows():
            if row["Code"]:
                new_vacs_dict[row["Code"]] = {"debut": row["Début"], "fin": row["Fin"]}
        new_conf["VACATIONS"] = new_vacs_dict
        
        st.session_state['config'] = new_conf
        save_config(new_conf) # Sauvegarde locale (temporaire sur Cloud)
        st.toast("Configuration mise à jour !", icon="💾")
        st.rerun()
