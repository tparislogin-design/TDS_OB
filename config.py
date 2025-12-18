# config.py

# --- PARAMÈTRES GÉNÉRAUX ---
ANNEE = 2025
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1lLtFisk983kJ-Yu0rtPyJAoweHxnsKwzen_J1rxsJes/edit?usp=drive_link"
SHEET_NAME = "Désidérata"

# --- CONTRAINTES SOLVEUR ---
SOLVER_TIME_LIMIT = 10  # Secondes
MIN_REST_HOURS = 11
MAX_HEURES_HEBDO = 36
MAX_CONSECUTIVE_SHIFTS = 4
MAX_WEEKEND_SHIFTS = 50
BUFFER_DAYS = 4  # Pour éviter les effets de bord
WEEKLY_REST_TYPE = 'sliding'

# --- COÛTS & POIDS ---
PENALTY_COST_J3_UNCOVERED = 30000
BALANCING_WEIGHT = 100
PREFERENCE_REWARD = 10

# --- LISTES & VACATIONS ---
CONTROLEURS = ['GAO', 'WBR', 'PLC', 'CML', 'BBD', 'LAK', 'MZN', 'TRT', 'CLO', 'FRD', 'DAZ', 'GNC', 'DTY', 'JCT', 'LNN', 'KGR']
CONTROLLERS_AFFECTES_BUREAU = ['GNC']

VACATIONS = ['M', 'J1', 'J2', 'J3', 'A1', 'A2', 'S']
HEURES_DEBUT = {'M': 5.5, 'J1': 7, 'J2': 8.5, 'J3': 8.5, 'A1': 12.5, 'A2': 15, 'S': 16}
HEURES_FIN = {'M': 14.5, 'J1': 16, 'J2': 18, 'J3': 18, 'A1': 22.5, 'A2': 23.5, 'S': 23.75}

PSEUDO_SHIFTS = ['B', 'B/']
PSEUDO_SHIFT_DURATIONS = {'B': 6.0, 'B/': 3.0}
PSEUDO_HEURES_DEBUT = {'B': 9.0, 'B/': None}
PSEUDO_HEURES_FIN = {'B': 16.0, 'B/': None}
PSEUDO_SHIFTS_COUNTED_FOR_MONTHLY_LIMIT = ['B']

# --- CONFIGURATION SPÉCIFIQUE (Tes règles complexes) ---
CONTROLLER_SPECIFIC_CONFIG = {
    'PLC': {'type': 'pair', 'pair_list': [('J1', 'M'), ('J2', 'M'), ('J3', 'M')]},
    'CLO': {'type': 'none', 'no_overlap_with': 'BBD', 'preferred_pair_list': [('M', 'J1'), ('J1', 'J2'), ('A2','S')], 'preferred_pair_reward': 15},
    'WBR': {'type': 'pair', 'pair_list': [('A2', 'A1'), ('S', 'A1'), ('S', 'A2')], 'preferred_pair_list': [('S', 'A1'), ('A2', 'A1')], 'preferred_pair_reward': 5},
    'TRT': {'preferences': {'weekday': ['J1', 'J2', 'J3'], 'weekend': ['A1','A2']}},
    'FRD': {'type': 'pair', 'pair_list': [('J2', 'M'), ('J1', 'M'), ('S', 'A1'),('J3', 'M'), ('A2', 'A1')]},
    'TCH': {'preferences': {'weekday': ['A1', 'A2', 'S'], 'weekend': ['A1','A2','S']}, 'preferred_pair_list': [('A1', 'S'), ('A2', 'A1'), ('J1','J3')], 'preferred_pair_reward': 4},
    'JCT': {'preferences': {'weekday': ['M','J1','J2'], 'weekend': ['M','J1','J2']}},
    'KGR': {'type': 'pair', 'pair_list': [('S', 'A1')], 'preferences': {'weekday': ['S','A1'], 'weekend': ['J1','J2','J3']}},
    # Ajouter les autres ici si besoin (MTS, CML, BBD, MZN, BUT, DTY...)
}

ALL_DEFINED_SHIFTS_CONFIG = VACATIONS + PSEUDO_SHIFTS
