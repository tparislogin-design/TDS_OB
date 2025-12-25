import pandas as pd
from datetime import date, timedelta, datetime
from ortools.sat.python import cp_model

def get_datetime_from_day_num(year, day_num):
    try:
        return datetime.combine(date(year, 1, 1) + timedelta(days=day_num - 1), datetime.min.time())
    except: return None

def run_solver(jour_debut, jour_fin, annee, config, pre_assignments={}):
    # 1. CONFIGURATION
    CONTROLEURS = config["CONTROLEURS"]
    VACATIONS_DATA = config["VACATIONS"]
    VACATIONS_CODES = list(VACATIONS_DATA.keys())
    PARAMS = config["CONTRAT"]
    
    # Conversion : Heures -> Centièmes (ex: 8.5 -> 850)
    DUREES_INT = {}
    for v, d in VACATIONS_DATA.items():
        debut = d['debut'] * 100
        fin = d['fin'] * 100
        # Gestion du cas nuit (ex: 23h - 06h = fin < debut)
        if fin < debut: 
            duree = (2400 - debut) + fin
        else:
            duree = fin - debut
        DUREES_INT[v] = int(duree)

    # Paramètres Contraintes
    MAX_H_SEMAINE_CAL = PARAMS.get("MAX_HOURS_WEEK_CALENDAR", 36) * 100
    MAX_H_GLISSANT = PARAMS.get("MAX_HOURS_7_ROLLING", 44) * 100
    # 2 jours consécutifs = une "paire de repos" obligatoire sur 7 jours
    MIN_PAIRES_REPOS_GLISSANT = 1 if PARAMS.get("REQUIRE_2_CONSECUTIVE_REST_DAYS", True) else 0

    # Période
    jour_fin_calc = jour_fin + PARAMS.get("BUFFER_DAYS", 4)
    jours_calcul = list(range(jour_debut, jour_fin_calc + 1))
    
    model = cp_model.CpModel()
    x = {} # Variables de travail (Agent, Vacation, Jour)
    is_worked = {} # Variables booléennes (Agent, Jour) -> Travaille ou pas ?

    # --- VARIABLES ---
    for c in CONTROLEURS:
        for j in jours_calcul:
            # Variable binaire: travaille-t-il ce jour là ?
            is_worked[c, j] = model.NewBoolVar(f'worked_{c}_{j}')
            
            vars_jour = []
            for v in VACATIONS_CODES:
                x[c, v, j] = model.NewBoolVar(f'x_{c}_{v}_{j}')
                vars_jour.append(x[c, v, j])
            
            # Lien: si une vacation est assignée, is_worked = 1
            model.Add(sum(vars_jour) == is_worked[c, j])
            # Unicité: Max 1 vacation par jour
            model.Add(sum(vars_jour) <= 1)

    # --- CONTRAINTES DE BASE ---
    
    # A. Couverture (Min 1 / vac / jour, sauf J3 optionnel)
    for j in jours_calcul:
        for v in VACATIONS_CODES:
            min_req = 0 if v == 'J3' else 1
            model.Add(sum(x[c, v, j] for c in CONTROLEURS) >= min_req)

    # B. Repos Quotidien (Enchaînement interdit si repos trop court)
    MIN_REST_INT = PARAMS.get("MIN_REST_HOURS", 11) * 100
    HEURES_FIN = {v: int(d['fin'] * 100) for v, d in VACATIONS_DATA.items()}
    HEURES_DEBUT = {v: int(d['debut'] * 100) for v, d in VACATIONS_DATA.items()}
    
    for c in CONTROLEURS:
        for j in range(jour_debut, jour_fin_calc):
            for v1 in VACATIONS_CODES:
                for v2 in VACATIONS_CODES:
                    fin_v1 = HEURES_FIN[v1]
                    debut_v2 = HEURES_DEBUT[v2] + 2400
                    if debut_v2 - fin_v1 < MIN_REST_INT:
                        model.Add(x[c, v1, j] + x[c, v2, j+1] <= 1)

    # C. Max Jours Consécutifs
    MAX_CONS = PARAMS.get("MAX_CONSECUTIVE_SHIFTS", 6)
    for c in CONTROLEURS:
        for i in range(len(jours_calcul) - MAX_CONS):
            window = [is_worked[c, jours_calcul[i+k]] for k in range(MAX_CONS + 1)]
            model.Add(sum(window) <= MAX_CONS)

    # --- NOUVELLES CONTRAINTES AVANCÉES ---

    # D. Max 36h / Semaine Calendaire (Lundi-Dimanche)
    # On groupe les jours par numéro de semaine ISO
    semaines_iso = {}
    for j in jours_calcul:
        dt = get_datetime_from_day_num(annee, j)
        if dt:
            # (Année, NuméroSemaine)
            iso_key = dt.isocalendar()[:2] 
            if iso_key not in semaines_iso: semaines_iso[iso_key] = []
            semaines_iso[iso_key].append(j)
    
    for c in CONTROLEURS:
        for sem, jours_sem in semaines_iso.items():
            # Somme des heures sur la semaine civile
            heures_semaine = []
            for j in jours_sem:
                for v in VACATIONS_CODES:
                    # Durée * Variable (0 ou 1)
                    heures_semaine.append(x[c, v, j] * DUREES_INT[v])
            model.Add(sum(heures_semaine) <= MAX_H_SEMAINE_CAL)

    # E. Max 44h / 7 Jours Glissants
    if len(jours_calcul) >= 7:
        for c in CONTROLEURS:
            for i in range(len(jours_calcul) - 7 + 1):
                fenetre_jours = jours_calcul[i : i + 7]
                heures_glissantes = []
                for j in fenetre_jours:
                    for v in VACATIONS_CODES:
                        heures_glissantes.append(x[c, v, j] * DUREES_INT[v])
                model.Add(sum(heures_glissantes) <= MAX_H_GLISSANT)

    # F. 2 Jours de Repos CONSÉCUTIFS sur 7 Jours Glissants
    # On définit une variable "est_paire_repos" pour chaque jour j (vrai si j et j+1 sont OFF)
    if MIN_PAIRES_REPOS_GLISSANT > 0 and len(jours_calcul) >= 8:
        for c in CONTROLEURS:
            is_repos_pair = {} 
            # On crée les variables de paires
            for j in range(jour_debut, jour_fin_calc): 
                # Une paire commence à j si j est OFF et j+1 est OFF
                # is_worked[j] + is_worked[j+1] == 0  <=> Repos consécutif
                pair_var = model.NewBoolVar(f'pair_off_{c}_{j}')
                
                # Logique : pair_var = 1 SI (worked[j] + worked[j+1] == 0)
                model.Add(is_worked[c, j] + is_worked[c, j+1] == 0).OnlyEnforceIf(pair_var)
                model.Add(is_worked[c, j] + is_worked[c, j+1] >= 1).OnlyEnforceIf(pair_var.Not())
                is_repos_pair[j] = pair_var

            # Fenêtre glissante de 7 jours
            # Sur 7 jours, il y a 6 opportunités de commencer une paire (J1-J2, J2-J3... J6-J7)
            for i in range(len(jours_calcul) - 7 + 1):
                debut_fenetre = jours_calcul[i]
                # On somme les variables "paire" qui commencent dans cette fenêtre
                # Attention : une paire qui commence le 7ème jour déborde, donc on regarde les 6 premiers jours de la fenêtre
                paires_dans_fenetre = []
                for k in range(6): 
                    j_pair = debut_fenetre + k
                    if j_pair in is_repos_pair:
                        paires_dans_fenetre.append(is_repos_pair[j_pair])
                
                if paires_dans_fenetre:
                    model.Add(sum(paires_dans_fenetre) >= MIN_PAIRES_REPOS_GLISSANT)

    # --- OBJECTIF ---
    # Minimiser l'écart type (équilibrage) - Simplifié
    max_shifts = model.NewIntVar(0, len(jours_calcul), 'max_s')
    for c in CONTROLEURS:
        model.Add(sum(is_worked[c, j] for j in jours_calcul) <= max_shifts)
    model.Minimize(max_shifts)

    # --- RÉSOLUTION ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(PARAMS.get("SOLVER_TIME_LIMIT", 10))
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        results = []
        for c in CONTROLEURS:
            row = {'Agent': c}
            for j in list(range(jour_debut, jour_fin + 1)):
                val = "OFF"
                for v in VACATIONS_CODES:
                    if solver.Value(x[c, v, j]):
                        val = v; break
                row[str(j)] = val
            results.append(row)
        return pd.DataFrame(results), ("Optimal" if status == cp_model.OPTIMAL else "Faisable")
    else:
        return None, "Infeasible"
