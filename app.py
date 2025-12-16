import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="TDS Manager Pro", layout="wide", initial_sidebar_state="collapsed")

# --- CSS POUR UN RENDU "APPLICATION BUREAU" ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 98% !important;}
    h1 {font-size: 1.5rem; color: #2c3e50;}
    .stButton button {width: 100%; border-radius: 4px;}
    </style>
""", unsafe_allow_html=True)

# --- EN-TÊTE ---
c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
with c1:
    st.title("✈️ TDS Manager | Planning Interactif")
with c2:
    st.metric("Contrôleurs", "14 Présents")
with c3:
    st.metric("Alertes", "0", delta_color="normal")
with c4:
    if st.button("💾 Sauvegarder"):
        st.toast("Planning sauvegardé avec succès !", icon="✅")

st.divider()

# --- GÉNÉRATION DES DONNÉES (Simulation Structure Matrice) ---
# Dans la vraie version, ceci viendra de Google Sheets ou de l'IA Or-Tools
def get_data():
    agents = ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN", "TRT", "CLO", "FRD", "DAZ", "GNC", "DTY", "JCT"]
    dates = [f"{i:02d}/01" for i in range(1, 32)] # 31 jours
    jours_sem = ["LU", "MA", "ME", "JE", "VE", "SA", "DI"] * 5
    
    rows = []
    for agent in agents:
        row = {"Agent": agent, "Solde": 0, "Objectif": 12}
        for i, d in enumerate(dates):
            col_name = f"{d}\n{jours_sem[i]}" # Saut de ligne dans l'en-tête
            # Remplissage par défaut vide
            row[col_name] = "" 
        rows.append(row)
    
    # Ajoutons quelques données pour l'exemple visuel
    df = pd.DataFrame(rows)
    # Simulation de quelques vacations
    cols = df.columns[3:] # On saute Agent, Solde, Objectif
    df.loc[0, cols[0]] = "M"   # GAO Matin le 1er
    df.loc[1, cols[0]] = "J1"  # WBR Jour le 1er
    df.loc[2, cols[0]] = "S"   # PLC Soir le 1er
    return df

df = get_data()

# --- CONFIGURATION AVANCÉE AG-GRID (Le coeur du rendu Pro) ---
gb = GridOptionsBuilder.from_dataframe(df)

# 1. Figer les colonnes de gauche (Noms + Compteurs)
gb.configure_column("Agent", pinned="left", width=100, cellStyle={'fontWeight': 'bold'})
gb.configure_column("Solde", pinned="left", width=70)
gb.configure_column("Objectif", pinned="left", width=80)

# 2. Javascript pour la coloration conditionnelle (Performance Max)
# C'est ce script qui tourne dans le navigateur pour colorier instantanément
cellStyleJS = JsCode("""
function(params) {
    if (params.value == 'M') {
        return {'backgroundColor': '#ffeebb', 'color': 'black', 'textAlign': 'center', 'fontWeight': 'bold'};
    }
    if (params.value == 'J1' || params.value == 'J2' || params.value == 'J3') {
        return {'backgroundColor': '#d4edda', 'color': 'black', 'textAlign': 'center'};
    }
    if (params.value == 'A1' || params.value == 'A2') {
        return {'backgroundColor': '#cce5ff', 'color': 'black', 'textAlign': 'center'};
    }
    if (params.value == 'S') {
        return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'textAlign': 'center', 'fontWeight': 'bold'};
    }
    if (params.value == 'OFF') {
        return {'backgroundColor': '#eeeeee', 'color': '#aaa', 'textAlign': 'center'};
    }
    return {'textAlign': 'center'};
}
""")

# 3. Appliquer le style et l'édition sur toutes les colonnes de dates
date_cols = df.columns[3:] # Toutes les colonnes sauf les 3 premières
for col in date_cols:
    gb.configure_column(col, 
                        width=60, 
                        editable=True, # Rend la cellule modifiable !
                        cellStyle=cellStyleJS)

# 4. Options globales de la grille
gb.configure_grid_options(rowHeight=35) # Hauteur de ligne confortable
gb.configure_selection('single') # Sélection simple

gridOptions = gb.build()

# --- AFFICHAGE DE LA GRILLE ---
st.caption("Double-cliquez sur une case pour modifier (M, J1, S, A1...). Les couleurs changent automatiquement.")

grid_response = AgGrid(
    df,
    gridOptions=gridOptions,
    allow_unsafe_jscode=True, # Nécessaire pour les couleurs JS
    enable_enterprise_modules=False,
    height=600, 
    width='100%',
    theme="balham", # Thème très compact et pro (style Excel)
    update_mode=GridUpdateMode.VALUE_CHANGED
)

# --- TABLEAU DE BORD EN TEMPS RÉEL (Bas de page) ---
# On récupère les données modifiées par l'utilisateur
df_modifie = grid_response['data']

st.divider()
c1, c2 = st.columns(2)
with c1:
    st.subheader("📊 Statistiques en direct")
    # Calcul simple d'exemple : compter combien de 'M' (Matins) sont posés
    total_matins = df_modifie.apply(lambda x: x.str.count('M') if x.dtype == "object" else 0, axis=1).sum().sum()
    st.info(f"Nombre total de vacations MATIN (M) : {int(total_matins)}")

with c2:
    st.subheader("🛠️ Actions Rapides")
    st.button("Vérifier la conformité (Légalités)", type="secondary")
