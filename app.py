import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from ortools.sat.python import cp_model

# --- CONFIGURATION ---
st.set_page_config(page_title="TDS Manager IA", layout="wide")

# --- STYLE CSS POUR LA LISIBILITÉ ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-title { color: #1e3a8a; font-weight: 800; font-size: 2rem; }
    .status-box { padding: 10px; border-radius: 5px; background: white; border: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTION D'OPTIMISATION (IA) ---
def optimiser_planning(agents, nb_jours, vacations):
    model = cp_model.CpModel()
    
    # Variables : planning[agent, jour, vacation]
    v_codes = [v['Code'] for v in vacations]
    v_map = {i: v for i, v in enumerate(v_codes)}
    
    assign = {}
    for a in agents:
        for j in range(nb_jours):
            for v_idx in range(len(v_codes)):
                assign[(a, j, v_idx)] = model.NewBoolVar(f'a{a}_j{j}_v{v_idx}')

    # CONTRAINTES
    # 1. Un seul service (ou repos) par jour par agent
    for a in agents:
        for j in range(nb_jours):
            model.AddExactlyOne(assign[(a, j, v_idx)] for v_idx in range(len(v_codes)))

    # 2. Couverture minimale : Au moins 1 agent sur M, J1 et S chaque jour
    # (On identifie les index de M, J1 et S)
    idx_M = v_codes.index('M')
    idx_J = v_codes.index('J1')
    idx_S = v_codes.index('S')
    
    for j in range(nb_jours):
        model.Add(sum(assign[(a, j, idx_M)] for a in agents) >= 1)
        model.Add(sum(assign[(a, j, idx_J)] for a in agents) >= 1)
        model.Add(sum(assign[(a, j, idx_S)] for a in agents) >= 1)

    # 3. Équité : Pas plus de 5 services par semaine par agent
    for a in agents:
        model.Add(sum(assign[(a, j, v)] for j in range(nb_jours) for v in range(len(v_codes)-1)) <= 15)

    # Résolution
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # On reconstruit le tableau
        res = []
        for a in agents:
            row = {"Agent": a}
            for j in range(nb_jours):
                for v_idx in range(len(v_codes)):
                    if solver.Value(assign[(a, j, v_idx)]):
                        row[j] = v_codes[v_idx]
            res.append(row)
        return pd.DataFrame(res)
    return None

# --- INTERFACE UTILISATEUR ---

st.markdown('<p class="main-title">✈️ TDS Manager : Planification Assistée par IA</p>', unsafe_allow_html=True)

# Barre d'actions
col_actions, col_status = st.columns([2, 1])
with col_actions:
    if st.button("🚀 LANCER L'OPTIMISATION IA", type="primary", use_container_width=True):
        with st.spinner("L'IA calcule la meilleure répartition..."):
            agents = ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN", "TRT", "CLO", "FRD"]
            vacs = [{"Code": "M"}, {"Code": "J1"}, {"Code": "A1"}, {"Code": "S"}, {"Code": "OFF"}]
            df_opti = optimiser_planning(agents, 14, vacs)
            if df_opti is not None:
                st.session_state['df_planning'] = df_opti
                st.success("Planning optimisé généré !")
            else:
                st.error("Impossible de trouver une solution avec ces contraintes.")

# Initialisation des données si vide
if 'df_planning' not in st.session_state:
    # Création d'un tableau vide par défaut
    agents = ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN", "TRT", "CLO", "FRD"]
    st.session_state['df_planning'] = pd.DataFrame([{"Agent": a, **{j: "OFF" for j in range(14)}} for a in agents])

# --- PRÉPARATION DE LA GRILLE AG-GRID ---
df = st.session_state['df_planning']
gb = GridOptionsBuilder.from_dataframe(df)

# JS pour la coloration et la lisibilité
# Ajout de la logique de couleur pour les colonnes (Weekend = Gris)
cell_style_jscode = JsCode("""
function(params) {
    // Couleurs des vacations
    if (params.value === 'M') return {'backgroundColor': '#FEF3C7', 'color': '#92400E', 'fontWeight': 'bold', 'textAlign': 'center'};
    if (params.value === 'S') return {'backgroundColor': '#FEE2E2', 'color': '#991B1B', 'fontWeight': 'bold', 'textAlign': 'center'};
    if (params.value === 'J1' || params.value === 'A1') return {'backgroundColor': '#D1FAE5', 'color': '#065F46', 'textAlign': 'center'};
    if (params.value === 'OFF') return {'backgroundColor': '#F3F4F6', 'color': '#9CA3AF', 'textAlign': 'center'};
    
    // Style par défaut
    return {'textAlign': 'center'};
}
""")

header_style_jscode = JsCode("""
function(params) {
    // On pourrait griser l'entête ici si besoin
}
""")

# Configuration des colonnes
gb.configure_column("Agent", pinned="left", width=120, cellStyle={'backgroundColor': '#FFFFFF', 'fontWeight': 'bold'})

# On boucle sur les jours pour appliquer le style et détecter les WE
jours_semaine = ["LU", "MA", "ME", "JE", "VE", "SA", "DI"] * 3
for i in range(14):
    jour_nom = jours_semaine[i]
    color_bg = '#F9FAFB' # Blanc cassé par défaut
    if jour_nom in ["SA", "DI"]:
        color_bg = '#E5E7EB' # Gris pour le WE
    
    gb.configure_column(str(i), 
                        headerName=f"{jour_nom} {i+1}", 
                        width=80, 
                        editable=True, 
                        cellStyle=cell_style_jscode)

gridOptions = gb.build()

# Affichage
st.subheader("Grille de Service Mensuelle")
AgGrid(
    df,
    gridOptions=gridOptions,
    allow_unsafe_jscode=True,
    theme="alpine", # Plus lisible et aéré que Balham
    height=500,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    reload_data=False
)

st.markdown("""
---
**Légende :** 🟡 **M** : Matin (05:45) | 🟢 **J/A** : Journée | 🔴 **S** : Soir (jusqu'à 23:30) | ⚪ **OFF** : Repos
""")
