import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import solver

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="TDS Manager", layout="wide", initial_sidebar_state="collapsed")

# --- 2. CSS "PIXEL PERFECT" ---
st.markdown("""
<style>
    .block-container {
        padding-top: 0rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem;
        max-width: 100% !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* HEADER */
    .custom-header {
        background-color: #ffffff; border-bottom: 1px solid #e0e0e0; padding: 10px 20px;
        display: flex; align-items: center; justify_content: space-between; margin-bottom: 15px;
    }
    .header-title {
        font-family: 'Segoe UI', sans-serif; font-size: 1.2rem; font-weight: 700; color: #1f1f1f;
        display: flex; align-items: center; gap: 10px;
    }
    .header-icon {
        background-color: #2563eb; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;
    }
    .nav-buttons {
        display: flex; gap: 5px; background-color: #f3f4f6; padding: 4px; border-radius: 6px;
    }
    .nav-btn {
        background: none; border: none; padding: 6px 15px; font-size: 0.9rem; font-weight: 500;
        color: #4b5563; cursor: pointer; border-radius: 4px;
    }
    .nav-btn.active {
        background-color: white; color: #2563eb; box-shadow: 0 1px 2px rgba(0,0,0,0.1); font-weight: 600;
    }

    /* PANNEAUX DROITE */
    .right-panel-card {
        background-color: white; border: 1px solid #e5e7eb; border-radius: 8px;
        padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .panel-header {
        font-size: 0.85rem; font-weight: 700; color: #374151; text-transform: uppercase;
        margin-bottom: 10px; display: flex; align-items: center; gap: 8px;
    }
    
    /* AG GRID HEADERS */
    .ag-header-cell-label .ag-header-cell-text {
        white-space: pre-wrap !important; text-align: center; font-size: 0.75rem; line-height: 1.1;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. FONCTIONS UTILITAIRES ---
def get_day_info(year, day_num):
    try:
        dt = datetime(year, 1, 1) + timedelta(days=day_num - 1)
        jours = ["LU", "MA", "ME", "JE", "VE", "SA", "DI"]
        return jours[dt.weekday()], dt.strftime("%d/%m")
    except:
        return "ERR", "00/00"

def load_config():
    if os.path.exists("config.json"):
        with open("config.json", 'r') as f: return json.load(f)
    return {"ANNEE": 2026, "CONTROLEURS": ["GAO", "WBR"]}

# --- 4. HEADER HTML ---
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
    <div style="width: 150px;"></div>
</div>
""", unsafe_allow_html=True)

# --- 5. LAYOUT PRINCIPAL ---
col_main, col_right = st.columns([78, 22], gap="medium")

if 'config' not in st.session_state: st.session_state['config'] = load_config()
config = st.session_state['config']

# === COLONNE DROITE ===
with col_right:
    with st.container():
        st.markdown('<div class="right-panel-card"><div class="panel-header">📗 SOURCE CSV</div>', unsafe_allow_html=True)
        st.text_input("URL", value="https://docs.google.com...", disabled=True, label_visibility="collapsed")
        st.button("📥 Importer", use_container_width=True, type="secondary")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="right-panel-card"><div class="panel-header">⚙ PARAMÈTRES</div>', unsafe_allow_html=True)
        c_annee = st.number_input("Année", value=config.get("ANNEE", 2026))
        c1, c2 = st.columns(2)
        with c1: jd = st.number_input("Début", value=365)
        with c2: jf = st.number_input("Fin", value=28)
        st.markdown("---")
        st.slider("Temps (s)", 5, 60, 25)
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.button("⚡ Lancer Optimisation", type="primary", use_container_width=True)

# === COLONNE PRINCIPALE ===
with col_main:
    # Toolbar
    tb1, tb2, tb3, tb4 = st.columns([2, 2, 4, 2])
    with tb1: st.button("👁 Voir Sources", use_container_width=True)
    with tb2: st.button("⚠ Voir Violations", use_container_width=True)
    with tb3: st.slider("Zoom", 50, 150, 100, label_visibility="collapsed")
    with tb4: st.button("⬇ Export Excel", use_container_width=True)

    # Data
    if 'df_planning' not in st.session_state:
        agents = config.get("CONTROLEURS", ["GAO", "WBR"])
        headers_def = {}
        cols = []
        
        # Génération headers (Fin 2025 -> Début 2026)
        year = config.get("ANNEE", 2026)
        days_list = [(year-1, 365)] + [(year, i) for i in range(1, 16)]
            
        for y, d in days_list:
            nom, date = get_day_info(y, d)
            col_id = f"{d}"
            cols.append(col_id)
            headers_def[col_id] = f"{nom}\n{d}\n{date}"

        data = [{"Agent": f"{a}\n0 / 12", **{c: "" for c in cols}} for a in agents]
        
        st.session_state['df_planning'] = pd.DataFrame(data)
        st.session_state['headers_def'] = headers_def

    df = st.session_state['df_planning']
    headers_mapping = st.session_state['headers_def']

    # AgGrid Config
    gb = GridOptionsBuilder.from_dataframe(df)
    
    gb.configure_column("Agent", pinned="left", width=80, cellStyle={
        'fontWeight': 'bold', 'backgroundColor': '#f8fafc', 
        'whiteSpace': 'pre-wrap', 'fontSize': '0.8rem', 'display': 'flex', 'alignItems': 'center'
    })

    # --- C'EST ICI QUE TU AVAIS L'ERREUR ---
    js_renderer = JsCode("""
    function(params) {
        if (!params.value) return {'textAlign': 'center', 'borderRight': '1px solid #eee'};
        const colors = {'M': '#fff7ed', 'J1': '#f0fdf4', 'J2': '#dcfce7', 'J3': '#bbf7d0', 'A1': '#eff6ff', 'A2': '#dbeafe', 'S': '#fef2f2'};
        const txtColors = {'M': '#c2410c', 'J1': '#15803d', 'J2': '#166534', 'J3': '#14532d', 'A1': '#1d4ed8', 'A2': '#1e40af', 'S': '#b91c1c'};
        return {
            'backgroundColor': colors[params.value] || 'white',
            'color': txtColors[params.value] || 'black',
            'fontWeight': 'bold', 'textAlign': 'center',
            'borderRight': '1px solid #eee', 'fontSize': '0.85rem'
        };
    }
    """)
    # ---------------------------------------

    for col in df.columns:
        if col != "Agent":
            gb.configure_column(col, headerName=headers_mapping.get(col, col), width=55, editable=True, cellStyle=js_renderer)

    gb.configure_grid_options(headerHeight=60, rowHeight=45, suppressMovableColumns=True)
    
    AgGrid(df, gridOptions=gb.build(), allow_unsafe_jscode=True, height=600, width='100%', theme="balham")
    st.caption("Clic Gauche : Verrouiller | Clic Droit : Refuser")
