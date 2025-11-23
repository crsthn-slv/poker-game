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
    
    return {
        'has_raises': raises > 0,
        'raise_count': raises,
        'call_count': calls,
        'last_action': last_action_type,
        'total_aggression': aggression
    }

