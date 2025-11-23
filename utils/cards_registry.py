"""
Registro global de cartas dos jogadores.
Permite acesso às cartas de todos os jogadores durante o round.
"""

# Registro global: UUID -> lista de cartas
_player_cards = {}


def store_player_cards(player_uuid, hole_cards):
    """Armazena as cartas de um jogador no registro.
    
    Args:
        player_uuid: UUID do jogador
        hole_cards: Lista de cartas do jogador (ex: ['SA', 'HK'])
    """
    if player_uuid and hole_cards:
        _player_cards[player_uuid] = hole_cards


def get_player_cards(player_uuid):
    """Obtém as cartas de um jogador do registro.
    
    Args:
        player_uuid: UUID do jogador
    
    Returns:
        Lista de cartas ou None se não encontrado
    """
    return _player_cards.get(player_uuid)


def get_all_cards():
    """Obtém todas as cartas armazenadas no registro.
    
    Returns:
        Dict {UUID: lista de cartas}
    """
    return _player_cards.copy()


def clear_registry():
    """Limpa o registro de cartas (chamado no início de cada round)."""
    global _player_cards
    _player_cards = {}


def remove_player_cards(player_uuid):
    """Remove as cartas de um jogador específico do registro.
    
    Args:
        player_uuid: UUID do jogador
    """
    if player_uuid in _player_cards:
        del _player_cards[player_uuid]
