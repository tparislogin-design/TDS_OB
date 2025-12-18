import pandas as pd
from datetime import date, timedelta, datetime
from ortools.sat.python import cp_model

# --- FONCTIONS UTILITAIRES ---
def get_datetime_from_day_num(year, day_num):
    try:
        return datetime.combine(date(year, 1, 1) + timedelta(days=day_num - 1), datetime.min.time())
    except: return None

# --- LE COEUR DU RÉACTEUR ---
def run_solver(jour_debut, jour_fin, annee, config, pre_assignments={}):
    """
    Fonction principale appelée par Streamlit.
    Accepte maintenant un dictionnaire 'config' dynamique.
    """
    
    # 1. Extraction de la configuration dynamique
    CONTROLEURS = config["CONTROLEURS"]
    VACATIONS_DATA = config["VACATIONS"] # Dict {code: {debut, fin}}
    VACATIONS_CODES = list(VACATIONS_DATA.keys())
    PARAMS = config["CONTRAT"]
    
    # Conversion des heures en entiers (centièmes) pour OR-Tools
    HEURES_DEBUT_INT = {v: int(d['debut'] * 100) for v, d in VACATIONS_DATA.items()}
    HEURES_FIN_INT = {v: int(d['fin'] * 100) for v, d in VACATIONS_DATA.items()}
    
    # 2. Période de calcul
    jour_fin_calc = jour_fin + PARAMS["BUFFER_DAYS"]
    jours_calcul = list(range(jour_debut, jour_fin_calc + 1))
    nb_jours = len(jours_calcul)
    max_shifts_period = int(nb_jours / 2) + 2 # Marge de sécurité

    model = cp_model.CpModel()
    x = {} 

    # --- VARIABLES ---
    for c in CONTROLEURS:
        for v in VACATIONS_CODES:
            for j in jours_calcul:
                x[c, v, j] = model.NewBoolVar(f'x_{c}_{v}_{j}')

    # --- CONTRAINTES ---
    
    # A. Unicité (1 shift max par jour)
    for c in CONTROLEURS:
        for j in jours_calcul:
            model.Add(sum(x[c, v, j] for v in VACATIONS_CODES) <= 1)

    # B. Pré-affectations
    for c, days_data in pre_assignments.items():
        if c in CONTROLEURS:
            for j, val in days_data.items():
                if j in jours_calcul and val in VACATIONS_CODES:
                     model.Add(x[c, val, j] == 1)
                elif j in jours_calcul and val == 'C': 
                     for v in VACATIONS_CODES: model.Add(x[c, v, j] == 0)

    # C. Couverture (Min 1 par vacation) - Simplifié
    for j in jours_calcul:
        for v in VACATIONS_CODES:
            vars_day = [x[c, v, j] for c in CONTROLEURS]
            # On peut rendre ça paramétrable plus tard
            if v != 'J3': 
                model.Add(sum(vars_day) >= 1)

    # D. Repos Quotidien
    BUREAU = config.get("CONTROLLERS_AFFECTES_BUREAU", [])
    MIN_REST = PARAMS["MIN_REST_HOURS"] * 100 # En centièmes
    
    for c in CONTROLEURS:
        if c in BUREAU: continue
        for j in range(jour_debut, jour_fin_calc): 
            for v1 in VACATIONS_CODES:
                for v2 in VACATIONS_CODES:
                    fin_v1 = HEURES_FIN_INT[v1]
                    debut_v2 = HEURES_DEBUT_INT[v2] + 2400 # +24h
                    if debut_v2 - fin_v1 < MIN_REST:
                        model.Add(x[c, v1, j] + x[c, v2, j+1] <= 1)

    # E. Contrainte Max Consécutifs
    MAX_CONS = PARAMS["MAX_CONSECUTIVE_SHIFTS"]
    for c in CONTROLEURS:
        for i in range(len(jours_calcul) - MAX_CONS):
            window = [sum(x[c, v, jours_calcul[i+k]] for v in VACATIONS_CODES) for k in range(MAX_CONS + 1)]
            model.Add(sum(window) <= MAX_CONS)

    # --- OBJECTIF : Équilibrage ---
    max_s = model.NewIntVar(0, max_shifts_period, 'max_s')
    for c in CONTROLEURS:
        nb_shifts = sum(x[c, v, j] for v in VACATIONS_CODES for j in jours_calcul)
        model.Add(nb_shifts <= max_s)
    model.Minimize(max_s)

    # --- RÉSOLUTION ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(PARAMS["SOLVER_TIME_LIMIT"])
    status = solver.Solve(model)

    results = []
    status_text = "Pas de solution"
    
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        status_text = "Optimale" if status == cp_model.OPTIMAL else "Faisable"
        for c in CONTROLEURS:
            row = {'Agent': c}
            for j in list(range(jour_debut, jour_fin + 1)):
                val = ""
                for v in VACATIONS_CODES:
                    if solver.Value(x[c, v, j]):
                        val = v
                        break
                if val == "" and pre_assignments.get(c, {}).get(j) == 'C': val = "C"
                elif val == "": val = "OFF"
                row[j] = val
            results.append(row)
        return pd.DataFrame(results), status_text
    else:
        return None, status_text
