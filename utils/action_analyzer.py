"""
Utilitário para analisar ações do round atual antes da decisão do bot.
Permite que os bots reajam em tempo real às ações dos oponentes.
"""


def analyze_current_round_actions(round_state, my_uuid):
    """
    Analisa ações do round atual antes da decisão do bot.
    
    Args:
        round_state: Estado atual do round (do PyPokerEngine)
        my_uuid: UUID do bot que está analisando
    
    Returns:
        dict com:
        - has_raises: bool (se alguém fez raise nesta street)
        - raise_count: int (quantos raises nesta street)
        - last_action: str (última ação: 'raise', 'call', 'fold' ou None)
        - total_aggression: float (0.0 a 1.0, nível de agressão observado)
        - call_count: int (quantos calls nesta street)
    """
    action_histories = round_state.get('action_histories', {})
    current_street = round_state.get('street', 'preflop')
    
    # Pega ações da street atual
    street_actions = action_histories.get(current_street, [])
    
    if not street_actions:
        return {
            'has_raises': False,
            'raise_count': 0,
            'call_count': 0,
            'last_action': None,
            'total_aggression': 0.0
        }
    
    # Analisa ações (excluindo as minhas)
    raises = 0
    calls = 0
    last_action_type = None
    
    for action in street_actions:
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != my_uuid:
            action_type = action.get('action', '').lower()
            if action_type == 'raise':
                raises += 1
                last_action_type = 'raise'
            elif action_type == 'call':
                calls += 1
                if last_action_type != 'raise':
                    last_action_type = 'call'
            elif action_type == 'fold':
                if last_action_type is None:
                    last_action_type = 'fold'
    
    total_actions = raises + calls
    aggression = raises / total_actions if total_actions > 0 else 0.0
    
    # Detecta campo passivo: muitos calls, nenhum raise
    is_passive = (raises == 0 and calls >= 2) or (raises == 0 and total_actions >= 1)
    
    # Calcula score de oportunidade de agressão quando campo está passivo
    passive_opportunity_score = 0.0
    if is_passive:
        # Mais calls = mais oportunidade
        passive_opportunity_score = min(1.0, calls / 3.0)  # Máximo 1.0 com 3+ calls
        # Pot pequeno aumenta oportunidade
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        if pot_size < 100:
            passive_opportunity_score += 0.2
        # Street inicial aumenta oportunidade
        if current_street in ['preflop', 'flop']:
            passive_opportunity_score += 0.15
        passive_opportunity_score = min(1.0, passive_opportunity_score)
    
    return {
        'has_raises': raises > 0,
        'raise_count': raises,
        'call_count': calls,
        'last_action': last_action_type,
        'total_aggression': aggression,
        'is_passive': is_passive,
        'passive_opportunity_score': passive_opportunity_score
    }


def analyze_possible_bluff(round_state, my_uuid, my_hand_strength, memory_manager=None):
    """
    Analisa se os oponentes podem estar blefando baseado em:
    - Ações do round atual (muitos raises = possível blefe)
    - Força da mão própria (para decidir se deve pagar)
    - Histórico de blefes dos oponentes (se disponível)
    
    Args:
        round_state: Estado atual do round
        my_uuid: UUID do bot
        my_hand_strength: Força da mão do bot (0-100)
        memory_manager: Gerenciador de memória (opcional, para histórico)
    
    Returns:
        dict com:
        - possible_bluff_probability: float (0.0 a 1.0, probabilidade de blefe)
        - should_call_bluff: bool (se deve pagar possível blefe)
        - bluff_confidence: float (confiança na análise)
        - analysis_factors: dict (fatores que indicam blefe)
    """
    # Analisa ações atuais
    current_actions = analyze_current_round_actions(round_state, my_uuid)
    
    # Probabilidade base de blefe
    bluff_prob = 0.0
    factors = {
        'multiple_raises': False,
        'high_aggression': False,
        'early_street': False,
        'small_pot': False,
        'opponent_bluff_history': False
    }
    
    # Fatores que indicam possível blefe:
    # 1. Muitos raises na street atual
    if current_actions['raise_count'] >= 2:
        bluff_prob += 0.4  # Muitos raises = possível blefe
        factors['multiple_raises'] = True
    elif current_actions['raise_count'] == 1:
        bluff_prob += 0.2  # Um raise = possível blefe
    
    # 2. Agressão alta (muitos raises vs calls)
    if current_actions['total_aggression'] > 0.6:
        bluff_prob += 0.2
        factors['high_aggression'] = True
    
    # 3. Street inicial (preflop/flop) = mais chance de blefe
    street = round_state.get('street', 'preflop')
    if street in ['preflop', 'flop']:
        bluff_prob += 0.1
        factors['early_street'] = True
    
    # 4. Pot pequeno = mais chance de blefe
    pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
    if pot_size < 50:
        bluff_prob += 0.1
        factors['small_pot'] = True
    
    # 5. Histórico de blefes do oponente (se disponível)
    if memory_manager:
        seats = round_state.get('seats', [])
        active_opponents = [s for s in seats
                          if isinstance(s, dict) and s.get('uuid') != my_uuid 
                          and s.get('state') == 'participating']
        
        for opp in active_opponents:
            opp_uuid = opp.get('uuid')
            if opp_uuid:
                opp_info = memory_manager.get_opponent_info(opp_uuid)
                if opp_info:
                    # Verifica histórico de blefes
                    recent_rounds = opp_info.get('rounds_against', [])[-5:]
                    if recent_rounds:
                        bluff_success_count = sum(1 for r in recent_rounds 
                                                 if r.get('analysis') == 'blefe_sucesso')
                        if bluff_success_count > 0:
                            bluff_rate = bluff_success_count / len(recent_rounds)
                            bluff_prob += 0.1 * min(bluff_rate, 0.5)
                            factors['opponent_bluff_history'] = True
    
    # Limita probabilidade entre 0 e 1
    bluff_prob = min(1.0, bluff_prob)
    
    # Decide se deve pagar possível blefe baseado na força da mão
    should_call = False
    if my_hand_strength >= 40:  # Mão forte: pode pagar blefe
        should_call = True
    elif my_hand_strength >= 30 and bluff_prob > 0.5:  # Mão média + alta chance de blefe
        should_call = True
    elif my_hand_strength >= 25 and bluff_prob > 0.7:  # Mão média-fraca + muito alta chance de blefe
        should_call = True
    
    # Confiança na análise
    confidence = 0.5  # Base
    if current_actions['raise_count'] >= 2:
        confidence += 0.2  # Mais confiança com múltiplos raises
    if memory_manager and active_opponents:
        confidence += 0.1  # Mais confiança com histórico
    
    return {
        'possible_bluff_probability': bluff_prob,
        'should_call_bluff': should_call,
        'bluff_confidence': min(1.0, confidence),
        'analysis_factors': factors
    }

