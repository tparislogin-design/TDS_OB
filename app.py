import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import config as cfg
import solver
from datetime import datetime

# --- CONFIGURATION DE LA PAGE (MODE LARGE) ---
st.set_page_config(page_title="TDS Manager Pro", layout="wide", initial_sidebar_state="expanded")

# --- CSS PRO (Injecté pour nettoyer l'interface) ---
st.markdown("""
<style>
    /* Réduire les marges blanches de Streamlit */
    .block-container {padding-top: 1rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem;}
    
    /* Titres plus élégants */
    h1 {color: #0f172a; font-family: 'Helvetica Neue', sans-serif; font-size: 1.8rem; font-weight: 700;}
    h3 {color: #334155; font-size: 1.2rem; margin-bottom: 0px;}
    
    /* Bouton principal stylisé */
    div.stButton > button:first-child {
        background-color: #2563eb; color: white; border-radius: 6px; border: none;
        padding: 0.5rem 1rem; font-weight: 600;
    }
    div.stButton > button:hover {background-color: #1d4ed8;}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR : CONTRÔLES ---
with st.sidebar:
    st.header("🎮 Pilotage")
    
    annee_select = st.number_input("Année", value=cfg.ANNEE, step=1)
    
    st.subheader("Période")
    c1, c2 = st.columns(2)
    with c1:
        jour_debut = st.number_input("Début (J)", value=335, min_value=1, max_value=365)
    with c2:
        jour_fin = st.number_input("Fin (J)", value=348, min_value=1, max_value=365)
        
    st.info(f"📅 Durée : {jour_fin - jour_debut + 1} jours")
    
    st.divider()
    
    # Bouton d'action principal
    btn_lancer = st.button("⚡ CALCULER LE PLANNING", type="primary", use_container_width=True)

# --- CORPS PRINCIPAL ---
st.title(f"Planning Opérationnel ATC")

# Logique de calcul
if btn_lancer:
    with st.spinner("🔄 Algorithme d'optimisation en cours..."):
        # Simulation données (à remplacer par tes vraies données)
        pre_assignments = {} 
        
        # Appel du moteur
        df_result, status = solver.run_solver(jour_debut, jour_fin, annee_select, pre_assignments)
        
        if df_result is not None:
            st.success(f"✅ Solution trouvée : {status}")
            st.session_state['df_planning'] = df_result
        else:
            st.error("❌ Aucune solution mathématique trouvée avec ces contraintes.")

# --- AFFICHAGE DU GRILLE (AG-GRID PRO) ---
if 'df_planning' in st.session_state:
    df = st.session_state['df_planning'].copy()
    
    # 1. Conversion CRITIQUE des noms de colonnes en texte (évite le crash .includes)
    df.columns = df.columns.astype(str)

    # 2. Configuration AgGrid
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # --- A. Colonne AGENT (Figée à gauche) ---
    gb.configure_column("Agent", pinned="left", width=100, cellStyle={
        'fontWeight': 'bold', 
        'backgroundColor': '#f8fafc', # Gris très clair
        'color': '#334155'
    })
    
    # --- B. Javascript pour le style des CELLULES (Shift Colors) ---
    # Couleurs pastels professionnelles, lisibles et douces pour les yeux
    js_cell_style = JsCode("""
    function(params) {
        // Couleurs des Vacations
        if (params.value == 'M')  return {'backgroundColor': '#fff7ed', 'color': '#9a3412', 'fontWeight': 'bold', 'textAlign': 'center', 'borderRight': '1px solid #e2e8f0'}; // Orange clair
        if (params.value == 'J1') return {'backgroundColor': '#f0fdf4', 'color': '#166534', 'fontWeight': 'bold', 'textAlign': 'center', 'borderRight': '1px solid #e2e8f0'}; // Vert clair
        if (params.value == 'J2') return {'backgroundColor': '#dcfce7', 'color': '#14532d', 'fontWeight': 'bold', 'textAlign': 'center', 'borderRight': '1px solid #e2e8f0'}; // Vert moyen
        if (params.value == 'J3') return {'backgroundColor': '#bbf7d0', 'color': '#052e16', 'fontWeight': 'bold', 'textAlign': 'center', 'borderRight': '1px solid #e2e8f0'}; // Vert fort
        if (params.value == 'A1') return {'backgroundColor': '#eff6ff', 'color': '#1e40af', 'fontWeight': 'bold', 'textAlign': 'center', 'borderRight': '1px solid #e2e8f0'}; // Bleu
        if (params.value == 'A2') return {'backgroundColor': '#dbeafe', 'color': '#1e3a8a', 'fontWeight': 'bold', 'textAlign': 'center', 'borderRight': '1px solid #e2e8f0'}; // Bleu fort
        if (params.value == 'S')  return {'backgroundColor': '#fef2f2', 'color': '#991b1b', 'fontWeight': 'bold', 'textAlign': 'center', 'borderRight': '1px solid #e2e8f0'}; // Rouge
        
        // Repos et Congés
        if (params.value == 'OFF') return {'backgroundColor': '#ffffff', 'color': '#cbd5e1', 'textAlign': 'center', 'fontSize': '0.8em'};
        if (params.value == 'C')   return {'backgroundColor': '#f1f5f9', 'color': '#64748b', 'textAlign': 'center', 'fontStyle': 'italic'};
        
        return {'textAlign': 'center', 'color': 'black'};
    }
    """)

    # --- C. Configuration des Colonnes JOURS ---
    cols_jours = [c for c in df.columns if c != 'Agent']
    
    for col_name in cols_jours:
        # Calcul des métadonnées du jour (Date, Weekend ?)
        header_label = col_name
        is_weekend = False
        try:
            day_int = int(col_name)
            dt = solver.get_datetime_from_day_num(annee_select, day_int)
            if dt:
                # Format court : "Lun 01"
                header_label = f"{dt.strftime('%a')[:2]}. {dt.day:02d}" 
                # Détection Samedi (6) ou Dimanche (7)
                if dt.isoweekday() >= 6:
                    is_weekend = True
        except:
            pass

        # Style de l'en-tête (Header)
        header_class = "weekend-header" if is_weekend else "weekday-header"
        
        # Style de la colonne (Column Background pour WE)
        # Si c'est un weekend, on grise légèrement le fond par défaut via JS si la cellule est vide/OFF
        
        gb.configure_column(
            col_name,
            headerName=header_label,
            width=65,       # Largeur fixe optimisée
            minWidth=60,
            maxWidth=70,
            cellStyle=js_cell_style,
            editable=True,  # Permettre la correction manuelle
            resizable=False # Empêcher de casser la mise en page
        )

    # --- D. Options Globales de la Grille ---
    gb.configure_grid_options(
        rowHeight=35,             # Hauteur compacte
        headerHeight=40,          # Hauteur en-tête
        suppressMovableColumns=True, # Empêcher de mélanger les colonnes
        enableRangeSelection=True # Permet de sélectionner plusieurs cases comme Excel
    )
    
    gridOptions = gb.build()

    # --- AFFICHAGE ---
    st.caption("Double-cliquez sur une case pour modifier manuellement (M, J1, S, OFF...).")
    
    AgGrid(
        df,
        gridOptions=gridOptions,
        allow_unsafe_jscode=True,
        height=600,         # Hauteur fixe du tableau
        width='100%',
        theme="balham",     # Thème "Balham" = Le plus compact et pro (style Excel)
        fit_columns_on_grid_load=False # False = permet le scroll horizontal si beaucoup de jours
    )
    
    # Export Excel
    st.download_button(
        label="📥 Exporter vers Excel",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f"planning_tds_{annee_select}_J{jour_debut}-{jour_fin}.csv",
        mime='text/csv'
    )

else:
    st.info("👋 Cliquez sur 'CALCULER LE PLANNING' dans la barre latérale pour démarrer.")
