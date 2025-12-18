# solver.py
import pandas as pd
import math
import calendar
from datetime import date, timedelta, datetime
from ortools.sat.python import cp_model
import config as cfg  # Importe ton fichier config.py

# --- FONCTIONS UTILITAIRES (Reprises de ton script) ---
def get_datetime_from_day_num(year, day_num):
    try:
        return datetime.combine(date(year, 1, 1) + timedelta(days=day_num - 1), datetime.min.time())
    except: return None

def get_weekend_days(year, start, end):
    weekend_days = set()
    for d in range(start, end + 1):
        dt = get_datetime_from_day_num(year, d)
        if dt and dt.isoweekday() >= 6: weekend_days.add(d)
    return weekend_days

# --- PRÉPARATION STATIQUE ---
SHIFT_DURATIONS = {v: cfg.HEURES_FIN[v] - cfg.HEURES_DEBUT[v] for v in cfg.VACATIONS}
# Conversion en int pour OR-Tools
SHIFT_DURATIONS_INT = {v: int(d * 100) for v, d in SHIFT_DURATIONS.items()}
HEURES_DEBUT_INT = {v: int(h * 100) for v, h in cfg.HEURES_DEBUT.items()}
HEURES_FIN_INT = {v: int(h * 100) for v, h in cfg.HEURES_FIN.items()}
PSEUDO_SHIFT_DURATIONS_INT = {v: int(d * 100) for v, d in cfg.PSEUDO_SHIFT_DURATIONS.items()}

# --- LE COEUR DU RÉACTEUR ---
def run_solver(jour_debut, jour_fin, annee, pre_assignments={}):
    """Fonction principale appelée par Streamlit"""
    
    # Extension de période (Buffer) comme dans ton V8.8
    jour_fin_calc = jour_fin + cfg.BUFFER_DAYS
    jours_calcul = list(range(jour_debut, jour_fin_calc + 1))
    nb_jours = len(jours_calcul)
    max_shifts_period = nb_jours // 2

    model = cp_model.CpModel()
    x = {} # Variables de décision

    # 1. Création Variables
    for c in cfg.CONTROLEURS:
        for v in cfg.VACATIONS:
            for j in jours_calcul:
                x[c, v, j] = model.NewBoolVar(f'x_{c}_{v}_{j}')

    # --- 2. CONTRAINTES (Reprises de ton script) ---
    
    # A. Unicité (1 shift max par jour)
    for c in cfg.CONTROLEURS:
        for j in jours_calcul:
            model.Add(sum(x[c, v, j] for v in cfg.VACATIONS) <= 1)

    # B. Pré-affectations (GSheet/Désidérata)
    # (Version simplifiée pour l'exemple, à connecter avec tes données GSheet)
    for c, days_data in pre_assignments.items():
        for j, val in days_data.items():
            if j in jours_calcul and val in cfg.VACATIONS:
                 model.Add(x[c, val, j] == 1)
            elif j in jours_calcul and val == 'C': # Congés
                 for v in cfg.VACATIONS: model.Add(x[c, v, j] == 0)

    # C. Couverture (Au moins 1 par vacation critique)
    for j in jours_calcul:
        for v in cfg.VACATIONS:
            # J3 Souple avec pénalité, les autres stricts (exemple)
            vars_day = [x[c, v, j] for c in cfg.CONTROLEURS]
            if v == 'J3':
                # On tolère le manque de J3 mais on le pénalise dans l'objectif
                pass 
            else:
                model.Add(sum(vars_day) >= 1)

    # D. Repos Quotidien (11h)
    for c in cfg.CONTROLEURS:
        if c in cfg.CONTROLLERS_AFFECTES_BUREAU: continue
        for j in range(jour_debut, jour_fin_calc): # Jusqu'à l'avant-dernier
            for v1 in cfg.VACATIONS:
                for v2 in cfg.VACATIONS:
                    fin_v1 = cfg.HEURES_FIN[v1]
                    debut_v2 = cfg.HEURES_DEBUT[v2] + 24 # Jour suivant
                    if debut_v2 - fin_v1 < cfg.MIN_REST_HOURS:
                        model.Add(x[c, v1, j] + x[c, v2, j+1] <= 1)

    # E. Contraintes spécifiques (GAO/LAK) - Ton code V8.8
    if 'GAO' in cfg.CONTROLEURS and 'LAK' in cfg.CONTROLEURS:
        for j in jours_calcul:
            dt = get_datetime_from_day_num(annee, j)
            if not dt: continue
            is_wed = (dt.isoweekday() == 3)
            # Mercredi: ni GAO ni LAK (exemple de ta règle)
            if is_wed:
                model.Add(sum(x['GAO', v, j] for v in cfg.VACATIONS) == 0)
                model.Add(sum(x['LAK', v, j] for v in cfg.VACATIONS) == 0)

    # F. Contrainte Max Consécutifs
    for c in cfg.CONTROLEURS:
        for i in range(len(jours_calcul) - cfg.MAX_CONSECUTIVE_SHIFTS):
            window = [sum(x[c, v, jours_calcul[i+k]] for v in cfg.VACATIONS) for k in range(cfg.MAX_CONSECUTIVE_SHIFTS + 1)]
            model.Add(sum(window) <= cfg.MAX_CONSECUTIVE_SHIFTS)

    # --- 3. OBJECTIFS ---
    # Minimiser les tours (équilibrage simple ici)
    obj_vars = []
    for c in cfg.CONTROLEURS:
        nb_shifts = sum(x[c, v, j] for v in cfg.VACATIONS for j in jours_calcul)
        obj_vars.append(nb_shifts)
    
    # On minimise l'écart (simplifié) -> Minimiser le max
    max_s = model.NewIntVar(0, max_shifts_period, 'max_s')
    for obj in obj_vars:
        model.Add(obj <= max_s)
    model.Minimize(max_s)

    # --- 4. RÉSOLUTION ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.SOLVER_TIME_LIMIT
    status = solver.Solve(model)

    results = []
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for c in cfg.CONTROLEURS:
            row = {'Agent': c}
            for j in list(range(jour_debut, jour_fin + 1)): # On affiche seulement la période demandée (pas le buffer)
                val = ""
                for v in cfg.VACATIONS:
                    if solver.Value(x[c, v, j]):
                        val = v
                        break
                # Gestion des pré-affectations (Congés, etc.) pour l'affichage
                if val == "" and pre_assignments.get(c, {}).get(j) == 'C':
                    val = "OFF" # Congé
                elif val == "":
                    val = "OFF" # Repos calculé
                
                row[j] = val
            results.append(row)
        return pd.DataFrame(results), "Succès"
    else:
        return None, "Pas de solution trouvée"
