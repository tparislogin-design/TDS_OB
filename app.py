import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

st.set_page_config(page_title="ATC Rostering", layout="wide")

st.title("🧩 ATC Rostering - Générateur de Planning Mensuel")

# --- 1. CONFIGURATION (D'après ton Image 1 & 2) ---
with st.sidebar:
    st.header("⚙️ Paramètres Généraux")
    max_consecutifs = st.number_input("Max jours consécutifs", value=4)
    repos_min_heures = st.number_input("Repos Min (heures)", value=11)
    
    st.header("🕒 Définition des Vacations")
    # On reproduit ton tableau de vacations (Image 2)
    data_vacations = [
        {"Code": "M", "Début": "05:45", "Fin": "12:45"},
        {"Code": "J1", "Début": "07:30", "Fin": "15:30"},
        {"Code": "J2", "Début": "08:00", "Fin": "16:00"},
        {"Code": "J3", "Début": "09:30", "Fin": "18:30"},
        {"Code": "A1", "Début": "13:00", "Fin": "22:00"},
        {"Code": "A2", "Début": "15:00", "Fin": "23:00"},
        {"Code": "S",  "Début": "16:45", "Fin": "23:30"},
        {"Code": "OFF", "Début": "00:00", "Fin": "00:00"} # Repos
    ]
    df_vacs = pd.DataFrame(data_vacations)
    st.dataframe(df_vacs, hide_index=True)

# --- 2. DONNÉES AGENTS (D'après ton Image 3) ---
col_param, col_main = st.columns([1, 3])

with col_param:
    st.subheader("👥 Agents")
    # Liste simplifiée basée sur ton image
    agents_list = ["GAO", "WBR", "PLC", "CML", "BBD", "LAK", "MZN"]
    selected_agents = st.multiselect("Sélectionner les agents", agents_list, default=agents_list)
    
    nb_jours = st.slider("Durée du planning (jours)", 7, 31, 7)

# --- 3. LE MOTEUR IA (Simulation OR-Tools) ---
if st.button("🚀 Lancer le calcul du Planning"):
    model = cp_model.CpModel()
    
    # Variables : planning[(agent, jour)] = code_vacation
    # Pour simplifier l'exemple, on associe chaque vacation à un entier (0=M, 1=J1, etc.)
    vacation_codes = df_vacs['Code'].tolist()
    map_vacation_int = {v: i for i, v in enumerate(vacation_codes)}
    
    shifts = {}
    for agent in selected_agents:
        for j in range(nb_jours):
            shifts[(agent, j)] = model.NewIntVar(0, len(vacation_codes)-1, f'shift_{agent}_{j}')

    # --- EXEMPLE DE CONTRAINTE : MAX CONSECUTIFS (Image 1) ---
    # Si un agent travaille, ce n'est pas "OFF". Supposons que "OFF" est le dernier code.
    idx_off = len(vacation_codes) - 1 
    
    for agent in selected_agents:
        for j in range(nb_jours - max_consecutifs):
            # On crée une liste de booléens : Est-ce qu'il travaille au jour j+k ?
            travaille_sequence = []
            for k in range(max_consecutifs + 1):
                is_working = model.NewBoolVar(f'working_{agent}_{j+k}')
                # Si shift != OFF, alors is_working = True
                model.Add(shifts[(agent, j+k)] != idx_off).OnlyEnforceIf(is_working)
                model.Add(shifts[(agent, j+k)] == idx_off).OnlyEnforceIf(is_working.Not())
                travaille_sequence.append(is_working)
            
            # La somme des jours travaillés sur une fenêtre de (Max+1) ne peut pas être égale à (Max+1)
            # Autrement dit : il faut au moins un repos dans le lot
            model.Add(sum(travaille_sequence) <= max_consecutifs)

    # --- RÉSOLUTION ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        st.success("✅ Solution trouvée !")
        
        # Préparation des données pour affichage
        res_data = []
        for agent in selected_agents:
            row = {"Agent": agent}
            total_services = 0
            for j in range(nb_jours):
                code_idx = solver.Value(shifts[(agent, j)])
                code_str = vacation_codes[code_idx]
                row[f"J{j+1}"] = code_str
                if code_str != "OFF":
                    total_services += 1
            row["Total"] = total_services # Pour reproduire ton compteur 0/12
            res_data.append(row)
            
        df_result = pd.DataFrame(res_data)
        
        # Affichage avec mise en forme conditionnelle
        def color_coding(val):
            if val == 'OFF': return 'background-color: #f0f2f6; color: #bcccdc'
            if val == 'M': return 'background-color: #ffeba0' # Jaune matin
            if val == 'S': return 'background-color: #ffcccb' # Rouge soir
            if val in ['J1', 'J2', 'J3']: return 'background-color: #90ee90' # Vert jour
            return ''

        st.dataframe(df_result.style.map(color_coding), use_container_width=True)
        
    else:
        st.error("❌ Pas de solution possible avec ces contraintes. Essaie d'assouplir les règles.")

else:
    st.info("Clique sur le bouton pour générer un planning test.")
