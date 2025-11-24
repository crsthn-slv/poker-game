"""
Registro global de cartas dos jogadores.
Permite acesso às cartas de todos os jogadores durante o round.

IMPORTANTE: Este registry sempre usa UUID fixo para garantir consistência.
"""
import os

# Registro global: UUID fixo -> lista de cartas
_player_cards = {}


def store_player_cards(player_uuid, hole_cards, player_name=None):
    """
    Armazena as cartas de um jogador no registro.
    
    IMPORTANTE: Sempre armazena com UUID fixo. Se player_uuid não for um UUID fixo,
    tenta mapear usando player_name.
    
    Args:
        player_uuid: UUID do jogador (pode ser UUID fixo ou UUID do PyPokerEngine)
        hole_cards: Lista de cartas do jogador (ex: ['SA', 'HK'])
        player_name: Nome do jogador (opcional, usado para mapear para UUID fixo)
    """
    if not player_uuid or not hole_cards:
        return
    
    # Tenta mapear para UUID fixo se tiver nome
    fixed_uuid = player_uuid
    if player_name:
        from utils.uuid_utils import get_bot_class_uuid_from_name, get_player_uuid
        mapped_uuid = get_bot_class_uuid_from_name(player_name)
        if not mapped_uuid:
            mapped_uuid = get_player_uuid(player_name)
        if mapped_uuid:
            fixed_uuid = mapped_uuid
            debug_mode = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'
            if debug_mode:
                print(f"[DEBUG] Registry: mapeado {player_uuid} -> {fixed_uuid} ({player_name})")
    
    _player_cards[fixed_uuid] = hole_cards


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
