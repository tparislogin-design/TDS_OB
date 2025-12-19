import streamlit as st
import pandas as pd
import json
import os
import math
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import solver

# --- 1. FONCTIONS UTILITAIRES (CONVERSION HEURES) ---
def decimal_to_hm(decimal_hour):
    """Convertit 6.5 en '06:30'"""
    try:
        hours = int(decimal_hour)
        minutes = int(round((decimal_hour - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"
    except:
        return "00:00"

def hm_to_decimal(hm_str):
    """Convertit '06:30' en 6.5"""
    try:
        if not hm_str or ":" not in hm_str: return 0.0
        h, m = map(int, hm_str.split(':'))
        return h + m / 60.0
    except:
        return 0.0

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="TDS Manager Pro", layout="wide", initial_sidebar_state="collapsed")

# CSS "Pixel Perfect" pour un rendu Application Métier
st.markdown("""
<style>
    /* Structure générale */
    .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 98% !important;}
    
    /* Onglets modernes */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; border-radius: 6px; border: 1px solid #e2e8f0; 
        background-color: white; color: #64748b; font-weight: 600; font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eff6ff; color: #2563eb; border-color: #2563eb;
    }

    /* Titres et Textes */
    h1 { font-family: 'Segoe UI', sans-serif; font-weight: 700; color: #0f172a; font-size: 1.5rem; margin-bottom: 0;}
    p, label { font-family: 'Segoe UI', sans-serif; font-size: 0.9rem; }
    
    /* Tableaux Streamlit natifs (Configuration) */
    [data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTION CONFIGURATION ---
CONFIG_FILE = "config.json"

def load_config():
    # Config par défaut de sécurité
    default = {
        "ANNEE": 2025,
        "CONTROLEURS": ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN"],
        "CONTROLLERS_AFFECTES_BUREAU": [],
        "VACATIONS": {"M": {"debut": 6.0, "fin": 14.0}, "S": {"debut": 15.0, "fin": 23.0}},
        "CONTRAT": {"MIN_REST_HOURS": 11, "MAX_CONSECUTIVE_SHIFTS": 4, "BUFFER_DAYS": 4, "SOLVER_TIME_LIMIT": 10}
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return default

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f: json.dump(cfg, f, indent=4)

if 'config' not in st.session_state: st.session_state['config'] = load_config()
config = st.session_state['config']

# --- 4. RENDERER JAVASCRIPT (AG-GRID PRO) ---
# Optimisé pour une lecture rapide : bordures fines, centrage parfait, couleurs sémantiques
RENDERER_JS = JsCode("""
function(params) {
    if (!params.value) return {'textAlign': 'center', 'backgroundColor': '#fff'};

    // Palette Pro (Pastel Sature)
    const styles = {
        'M':  {bg: '#fff7ed', text: '#c2410c', border: '#fed7aa'}, // Orange Matin
        'J1': {bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0'}, // Vert Jour 1
        'J2': {bg: '#dcfce7', text: '#166534', border: '#86efac'}, // Vert Jour 2
        'J3': {bg: '#bbf7d0', text: '#14532d', border: '#4ade80'}, // Vert Jour 3
        'A1': {bg: '#eff6ff', text: '#1d4ed8', border: '#bfdbfe'}, // Bleu Après-Midi
        'A2': {bg: '#dbeafe', text: '#1e40af', border: '#93c5fd'}, // Bleu Soir
        'S':  {bg: '#fef2f2', text: '#b91c1c', border: '#fecaca'}, // Rouge Soirée
        'OFF':{bg: '#f8fafc', text: '#94a3b8', border: '#e2e8f0'}, // Gris Repos
        'C':  {bg: '#f1f5f9', text: '#64748b', border: '#e2e8f0'}  // Gris Congés
    };

    const style = styles[params.value] || {bg: 'white', text: 'black', border: '#eee'};

    return {
        'backgroundColor': style.bg,
        'color': style.text,
        'fontWeight': '600',
        'textAlign': 'center',
        'borderRight': '1px solid ' + style.border, 
        'borderBottom': '1px solid #f1f5f9',
        'fontSize': '0.9em'
    };
}
""")

# --- 5. INTERFACE ---
c_titre, c_save = st.columns([6, 1])
with c_titre: st.title("✈️ TDS Manager Pro")

tab_plan, tab_conf = st.tabs(["📅 PLANNING OPÉRATIONNEL", "⚙️ CONFIGURATION"])

# =========================================================
# ONGLET 1 : PLANNING
# =========================================================
with tab_plan:
    # Barre de contrôle compacte
    with st.container():
        c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
        with c1: annee = st.number_input("Année", value=config["ANNEE"], step=1)
        with c2: j_start = st.number_input("J. Début", value=335, min_value=1)
        with c3: j_end = st.number_input("J. Fin", value=348, min_value=1)
        with c4:
            st.write("") 
            if st.button("⚡ LANCER LE CALCUL (OR-TOOLS)", type="primary", use_container_width=True):
                with st.spinner("Optimisation mathématique en cours..."):
                    res, stat = solver.run_solver(j_start, j_end, annee, config, {})
                    if res is not None:
                        st.session_state['df_planning'] = res
                        st.toast(f"Calcul réussi : {stat}", icon="✅")
                    else: st.error("Pas de solution possible.")

    st.write("")
    
    # Affichage du tableau AgGrid Optimisé
    if 'df_planning' in st.session_state:
        df = st.session_state['df_planning'].copy()
        df.columns = df.columns.astype(str) # Important pour le JS
        
        gb = GridOptionsBuilder.from_dataframe(df)
        
        # 1. Colonne Agent (Figée)
        gb.configure_column("Agent", pinned="left", width=95, cellStyle={
            'fontWeight': '700', 'backgroundColor': '#f8fafc', 'color': '#334155', 
            'borderRight': '2px solid #e2e8f0', 'display': 'flex', 'alignItems': 'center'
        })

        # 2. Colonnes Jours (Dynamiques)
        cols_jours = [c for c in df.columns if c != 'Agent']
        for col in cols_jours:
            header = col
            is_we = False
            try:
                # Formatage intelligent : "Lu 01"
                d_int = int(col)
                dt = solver.get_datetime_from_day_num(annee, d_int)
                if dt:
                    header = f"{dt.strftime('%a')[:2]}. {dt.day:02d}"
                    if dt.isoweekday() >= 6: is_we = True
            except: pass
            
            gb.configure_column(
                col,
                headerName=header,
                width=62, # Largeur idéale pour "Code Vacation"
                cellStyle=RENDERER_JS,
                editable=True,
                cellClass="weekend-col" if is_we else "" # Classe CSS pour le WE (optionnelle)
            )

        # 3. Options Globales
        gb.configure_grid_options(
            rowHeight=35, 
            headerHeight=38,
            suppressMovableColumns=True,
            enableCellChangeFlash=True
        )
        
        AgGrid(df, gridOptions=gb.build(), allow_unsafe_jscode=True, height=550, theme="balham", width='100%')
    else:
        st.info("👋 Cliquez sur 'LANCER LE CALCUL' pour générer le planning.")

# =========================================================
# ONGLET 2 : CONFIGURATION (AVEC HEURES LISIBLES)
# =========================================================
with tab_conf:
    col_l, col_r = st.columns([1, 2], gap="large")

    # --- Section Agents ---
    with col_l:
        st.subheader("👥 Contrôleurs")
        st.caption("Liste des indicatifs (un par ligne)")
        agents_text = st.text_area("Agents", value="\n".join(config["CONTROLEURS"]), height=300, label_visibility="collapsed")

    # --- Section Paramètres & Vacations ---
    with col_r:
        st.subheader("⚙️ Paramètres")
        cc1, cc2, cc3 = st.columns(3)
        with cc1: mc = st.number_input("Max Consécutifs", value=config["CONTRAT"]["MAX_CONSECUTIVE_SHIFTS"])
        with cc2: mr = st.number_input("Repos Min (h)", value=config["CONTRAT"]["MIN_REST_HOURS"])
        with cc3: tm = st.number_input("Timeout (s)", value=config["CONTRAT"]["SOLVER_TIME_LIMIT"])
        
        st.divider()
        st.subheader("🕒 Horaires des Vacations")
        st.caption("Modifiez les heures au format HH:MM (ex: 06:30)")

        # --- CONVERSION DYNAMIQUE POUR L'AFFICHAGE ---
        # 1. On transforme le JSON (decimal) en DataFrame (HH:MM)
        vacs_list = []
        for code, times in config["VACATIONS"].items():
            vacs_list.append({
                "Code": code,
                "Début": decimal_to_hm(times["debut"]), # 6.5 -> "06:30"
                "Fin": decimal_to_hm(times["fin"])      # 14.0 -> "14:00"
            })
        df_vacs_display = pd.DataFrame(vacs_list)

        # 2. Éditeur Interactif
        edited_df = st.data_editor(
            df_vacs_display, 
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Code": st.column_config.TextColumn("Code", width="small", disabled=False),
                "Début": st.column_config.TextColumn("Début (HH:MM)", width="medium", validate="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"),
                "Fin": st.column_config.TextColumn("Fin (HH:MM)", width="medium", validate="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
            },
            hide_index=True
        )

    # --- BOUTON SAUVEGARDE ---
    st.write("---")
    if st.button("💾 ENREGISTRER TOUS LES CHANGEMENTS", type="primary"):
        # 1. Agents
        new_agents = [x.strip() for x in agents_text.split('\n') if x.strip()]
        
        # 2. Vacations (Reconversion HH:MM -> Decimal)
        new_vacs = {}
        for idx, row in edited_df.iterrows():
            if row["Code"]:
                new_vacs[row["Code"]] = {
                    "debut": hm_to_decimal(row["Début"]), # "06:30" -> 6.5
                    "fin": hm_to_decimal(row["Fin"])
                }
        
        # 3. Construction Config
        new_conf = config.copy()
        new_conf["CONTROLEURS"] = new_agents
        new_conf["VACATIONS"] = new_vacs
        new_conf["CONTRAT"]["MAX_CONSECUTIVE_SHIFTS"] = mc
        new_conf["CONTRAT"]["MIN_REST_HOURS"] = mr
        new_conf["CONTRAT"]["SOLVER_TIME_LIMIT"] = tm
        
        # 4. Save
        st.session_state['config'] = new_conf
        save_config(new_conf)
        st.toast("Configuration sauvegardée avec succès !", icon="✅")
        st.rerun()
