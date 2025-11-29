"""
Tabela de Equidade Pré-Flop (Win Rates).
Baseado em simulações de Monte Carlo contra mão aleatória (Heads-Up).
Valores aproximados em porcentagem (0-100).

Formato das chaves:
- Pares: 'AA', 'KK', '22'
- Naipes Iguais (Suited): 'AKs', 'T9s' (Maior carta primeiro)
- Naipes Diferentes (Offsuit): 'AKo', 'T9o' (Maior carta primeiro)
"""

PREFLOP_EQUITY = {
    # --- PARES ---
    'AA': 85.0, 'KK': 82.0, 'QQ': 80.0, 'JJ': 77.0, 'TT': 75.0,
    '99': 72.0, '88': 69.0, '77': 66.0, '66': 63.0, '55': 60.0,
    '44': 57.0, '33': 54.0, '22': 50.0,

    # --- SUITED (Naipes Iguais) ---
    'AKs': 67.0, 'AQs': 66.0, 'AJs': 65.0, 'ATs': 64.0, 'A9s': 62.0, 'A8s': 61.0, 'A7s': 60.0, 'A6s': 59.0, 'A5s': 59.0, 'A4s': 58.0, 'A3s': 57.0, 'A2s': 56.0,
    'KQs': 63.0, 'KJs': 62.0, 'KTs': 61.0, 'K9s': 59.0, 'K8s': 57.0, 'K7s': 56.0, 'K6s': 55.0, 'K5s': 54.0, 'K4s': 53.0, 'K3s': 52.0, 'K2s': 51.0,
    'QJs': 60.0, 'QTs': 59.0, 'Q9s': 57.0, 'Q8s': 55.0, 'Q7s': 53.0, 'Q6s': 52.0, 'Q5s': 51.0, 'Q4s': 50.0, 'Q3s': 49.0, 'Q2s': 48.0,
    'JTs': 57.0, 'J9s': 55.0, 'J8s': 53.0, 'J7s': 51.0, 'J6s': 49.0, 'J5s': 48.0, 'J4s': 47.0, 'J3s': 46.0, 'J2s': 45.0,
    'T9s': 54.0, 'T8s': 52.0, 'T7s': 50.0, 'T6s': 48.0, 'T5s': 46.0, 'T4s': 45.0, 'T3s': 44.0, 'T2s': 43.0,
    '98s': 51.0, '97s': 49.0, '96s': 47.0, '95s': 45.0, '94s': 43.0, '93s': 42.0, '92s': 41.0,
    '87s': 48.0, '86s': 46.0, '85s': 44.0, '84s': 42.0, '83s': 41.0, '82s': 40.0,
    '76s': 45.0, '75s': 43.0, '74s': 41.0, '73s': 39.0, '72s': 38.0,
    '65s': 42.0, '64s': 40.0, '63s': 39.0, '62s': 37.0,
    '54s': 40.0, '53s': 38.0, '52s': 36.0,
    '43s': 37.0, '42s': 35.0,
    '32s': 34.0,

    # --- OFFSUIT (Naipes Diferentes) ---
    'AKo': 65.0, 'AQo': 64.0, 'AJo': 63.0, 'ATo': 62.0, 'A9o': 60.0, 'A8o': 59.0, 'A7o': 58.0, 'A6o': 57.0, 'A5o': 57.0, 'A4o': 56.0, 'A3o': 55.0, 'A2o': 54.0,
    'KQo': 61.0, 'KJo': 60.0, 'KTo': 59.0, 'K9o': 57.0, 'K8o': 55.0, 'K7o': 54.0, 'K6o': 53.0, 'K5o': 52.0, 'K4o': 51.0, 'K3o': 50.0, 'K2o': 49.0,
    'QJo': 58.0, 'QTo': 57.0, 'Q9o': 55.0, 'Q8o': 53.0, 'Q7o': 51.0, 'Q6o': 50.0, 'Q5o': 49.0, 'Q4o': 48.0, 'Q3o': 47.0, 'Q2o': 46.0,
    'JTo': 55.0, 'J9o': 53.0, 'J8o': 51.0, 'J7o': 49.0, 'J6o': 47.0, 'J5o': 46.0, 'J4o': 45.0, 'J3o': 44.0, 'J2o': 43.0,
    'T9o': 52.0, 'T8o': 50.0, 'T7o': 48.0, 'T6o': 46.0, 'T5o': 44.0, 'T4o': 43.0, 'T3o': 42.0, 'T2o': 41.0,
    '98o': 49.0, '97o': 47.0, '96o': 45.0, '95o': 43.0, '94o': 41.0, '93o': 40.0, '92o': 39.0,
    '87o': 46.0, '86o': 44.0, '85o': 42.0, '84o': 40.0, '83o': 39.0, '82o': 38.0,
    '76o': 43.0, '75o': 41.0, '74o': 39.0, '73o': 37.0, '72o': 36.0,
    '65o': 40.0, '64o': 38.0, '63o': 37.0, '62o': 35.0,
    '54o': 38.0, '53o': 36.0, '52o': 34.0,
    '43o': 35.0, '42o': 33.0,
    '32o': 32.0
}

def get_preflop_equity(hole_card: list) -> float:
    """
    Retorna a equidade pré-flop (0-100) para uma mão.
    
    Args:
        hole_card: Lista de 2 cartas (ex: ['SA', 'HK'])
        
    Returns:
        float: Equidade (ex: 65.0 para AKo)
    """
    if not hole_card or len(hole_card) != 2:
        return 0.0
        
    # Extrai ranks e suits
    # Formato esperado: 'SA' (SuitRank) ou 'AS' (RankSuit)?
    # O padrão do PyPokerEngine é SuitRank (ex: 'SA' = Spades Ace)
    # Mas precisamos verificar o formato exato que está vindo.
    # Assumindo SuitRank (ex: 'SA', 'HK')
    
    c1, c2 = hole_card
    s1, r1 = c1[0], c1[1]
    s2, r2 = c2[0], c2[1]
    
    # Mapeia ranks para valores para ordenação
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
        '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    
    v1 = rank_map.get(r1, 0)
    v2 = rank_map.get(r2, 0)
    
    # Ordena: Maior primeiro
    if v1 < v2:
        r1, r2 = r2, r1
        s1, s2 = s2, s1
        v1, v2 = v2, v1
        
    # Constrói chave
    if v1 == v2:
        key = f"{r1}{r2}" # Par (ex: AA)
    elif s1 == s2:
        key = f"{r1}{r2}s" # Suited (ex: AKs)
    else:
        key = f"{r1}{r2}o" # Offsuit (ex: AKo)
        
    return PREFLOP_EQUITY.get(key, 0.0)
