"""
Registro global de cartas dos jogadores.
Permite acesso às cartas de todos os jogadores durante o round.

IMPORTANTE: Todos os UUIDs são sempre fixos e determinísticos.
"""
import os

# Registro global: UUID fixo -> lista de cartas
_player_cards = {}


def store_player_cards(player_uuid, hole_cards, player_name=None):
    """
    Armazena as cartas de um jogador no registro.
    
    Args:
        player_uuid: UUID do jogador (sempre fixo)
        hole_cards: Lista de cartas do jogador (ex: ['SA', 'HK'])
        player_name: Nome do jogador (opcional, para debug)
    """
    if not player_uuid or not hole_cards:
        return
    
    # UUID já é sempre fixo, armazena diretamente
    _player_cards[player_uuid] = hole_cards
    
    debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
    if debug_mode and player_name:
        print(f"[DEBUG] Registry: armazenado {player_uuid} ({player_name})")


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
