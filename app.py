import streamlit as st
import pandas as pd
from datetime import date, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from ortools.sat.python import cp_model

# --- CONFIGURATION DE LA PAGE (LARGE ET PROPRE) ---
st.set_page_config(page_title="TDS Planner IA", layout="wide", initial_sidebar_state="collapsed")

# --- CSS POUR AMÉLIORER LA LISIBILITÉ ---
st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98%;}
    h1 {font-size: 1.8rem; color: #1e3a8a;}
    .stButton button {background-color: #1e3a8a; color: white; border-radius: 5px; font-weight: bold;}
    .st-emotion-cache-1kyc28m {justify-content: center;} /* Centre les en-têtes de colonnes */
    </style>
""", unsafe_allow_html=True)

# --- DONNÉES DE BASE (VACATIONS) ---
VACATIONS = {
    'M': {'start': '05:45', 'end': '12:45', 'color': '#fef08a'}, # Jaune clair
    'J1': {'start': '07:30', 'end': '15:30', 'color': '#bbf7d0'}, # Vert clair
    'J2': {'start': '08:00', 'end': '16:00', 'color': '#bbf7d0'},
    'J3': {'start': '09:30', 'end': '18:30', 'color': '#bbf7d0'},
    'A1': {'start': '13:00', 'end': '22:00', 'color': '#bfdbfe'}, # Bleu clair
    'A2': {'start': '15:00', 'end': '23:00', 'color': '#bfdbfe'},
    'S': {'start': '16:45', 'end': '23:30', 'color': '#fecaca'}, # Rouge clair
    'OFF': {'start': '00:00', 'end': '00:00', 'color': '#f1f5f9'} # Gris très clair
}
CODES_TRAVAIL = [k for k in VACATIONS if k != 'OFF']

# --- FONCTION D'OPTIMISATION (LE MOTEUR IA) ---
def run_optimization(agents, nb_jours, couverture_min, max_consecutifs):
    model = cp_model.CpModel()
    
    # 1. Variables : planning[agent][jour] = index de la vacation
    vacation_list = list(VACATIONS.keys())
    shifts = {}
    for agent in agents:
        for j in range(nb_jours):
            shifts[(agent, j)] = model.NewIntVar(0, len(vacation_list) - 1, f'shift_{agent}_{j}')

    # 2. Contraintes
    # A. Couverture minimale : chaque jour, il doit y avoir au moins X personnes qui travaillent
    idx_off = vacation_list.index('OFF')
    for j in range(nb_jours):
        travaillent_ce_jour = [model.NewBoolVar(f'work_{a}_{j}') for a in agents]
        for i, agent in enumerate(agents):
            model.Add(shifts[(agent, j)] != idx_off).OnlyEnforceIf(travaillent_ce_jour[i])
            model.Add(shifts[(agent, j)] == idx_off).OnlyEnforceIf(travaillent_ce_jour[i].Not())
        model.Add(sum(travaillent_ce_jour) >= couverture_min)

    # B. Max jours de travail consécutifs
    for agent in agents:
        for j in range(nb_jours - max_consecutifs):
            model.Add(sum(shifts[(agent, j + k)] != idx_off for k in range(max_consecutifs + 1)) <= max_consecutifs)

    # 3. Résolution
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0 # Temps limite
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        rows = []
        for agent in agents:
            row = {"Agent": agent, "Solde": 0}
            for j in range(nb_jours):
                code_idx = solver.Value(shifts[(agent, j)])
                row[f"J{j+1}"] = vacation_list[code_idx]
            rows.append(row)
        return pd.DataFrame(rows)
    else:
        return None

# --- INTERFACE UTILISATEUR ---
st.title("✈️ TDS Planner IA")
st.markdown("---")

# Layout à deux colonnes : Panneau de contrôle à gauche, Planning à droite
col_controles, col_planning = st.columns([1, 4])

with col_controles:
    st.header("Panneau de Contrôle")
    
    agents_list = ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN", "TRT", "CLO", "FRD"]
    nb_jours = st.slider("Jours à planifier", 7, 31, 14)
    
    st.subheader("Contraintes de l'IA")
    couverture_min = st.slider("Couverture minimale (agents/jour)", 1, len(agents_list), 5)
    max_consecutifs = st.slider("Max jours de travail consécutifs", 3, 7, 5)

    if st.button("🚀 Lancer l'Optimisation", use_container_width=True):
        with st.spinner("L'IA calcule le meilleur planning..."):
            result_df = run_optimization(agents_list, nb_jours, couverture_min, max_consecutifs)
            if result_df is not None:
                st.session_state.planning_df = result_df # Sauvegarde du résultat
                st.success("Planning généré avec succès !")
            else:
                st.error("Aucune solution trouvée. Essayez d'assouplir les contraintes.")

# Initialisation du DataFrame dans l'état de la session
if 'planning_df' not in st.session_state:
    st.session_state.planning_df = pd.DataFrame(columns=["Agent", "Solde"] + [f"J{i+1}" for i in range(14)])

with col_planning:
    st.header("🗓️ Grille de Planning")
    
    # --- CONFIGURATION AG-GRID (LISIBILITÉ AMÉLIORÉE) ---
    df_display = st.session_state.planning_df.copy()
    
    # Renommer les colonnes pour afficher Date + Jour
    start_date = date(2026, 1, 1)
    new_cols = {}
    for i, col in enumerate(df_display.columns):
        if col.startswith("J"):
            current_date = start_date + timedelta(days=i-2)
            day_name = current_date.strftime("%a").upper()[:2]
            new_cols[col] = f"{current_date.day:02d}/{current_date.month:02d}\n{day_name}"
    df_display.rename(columns=new_cols, inplace=True)

    gb = GridOptionsBuilder.from_dataframe(df_display)
    
    # JS pour coloration dynamique et mise en évidence des week-ends
    cellStyleJS = JsCode(f"""
    function(params) {{
        // Style de base
        let style = {{'textAlign': 'center', 'borderRight': '1px solid #eee'}};

        // Mise en évidence des week-ends
        if (params.colDef.headerName.includes('SA') || params.colDef.headerName.includes('DI')) {{
            style.backgroundColor = '#f8fafc'; // Gris très léger pour le fond du week-end
        }}
        
        // Coloration par code vacation
        const colors = { {k: v['color'] for k, v in VACATIONS.items()} };
        if (colors[params.value]) {{
            style.backgroundColor = colors[params.value];
            style.fontWeight = 'bold';
            style.color = '#334155'; // Texte sombre pour le contraste
        }}
        
        return style;
    }}
    """)

    gb.configure_columns(df_display.columns[2:], cellStyle=cellStyleJS, editable=True, width=70)
    gb.configure_column("Agent", pinned="left", width=100, cellStyle={'fontWeight': 'bold'})
    gb.configure_column("Solde", pinned="left", width=70)
    
    gb.configure_grid_options(rowHeight=40, headerHeight=50)
    gridOptions = gb.build()

    AgGrid(
        df_display,
        gridOptions=gridOptions,
        allow_unsafe_jscode=True,
        theme="alpine", # Thème plus aéré et moderne
        height=600,
        enable_enterprise_modules=False
    )
