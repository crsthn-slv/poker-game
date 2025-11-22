"""
Registro global de cartas dos jogadores durante cada round.
Usado para expor as cartas de todos os jogadores no resultado final.
"""
from typing import Dict, List, Optional

# Dicionário global: {player_uuid: hole_cards}
ROUND_CARDS: Dict[str, List[str]] = {}


def store_player_cards(player_uuid: str, hole_cards: List[str]) -> None:
    """
    Armazena as cartas de um jogador no registro.
    
    Args:
        player_uuid: UUID do jogador
        hole_cards: Lista de cartas do jogador (ex: ['SA', 'HK'])
    """
    if player_uuid and hole_cards:
        ROUND_CARDS[player_uuid] = hole_cards


def get_player_cards(player_uuid: str) -> Optional[List[str]]:
    """
    Obtém as cartas de um jogador do registro.
    
    Args:
        player_uuid: UUID do jogador
    
    Returns:
        Lista de cartas do jogador ou None se não encontrado
    """
    return ROUND_CARDS.get(player_uuid)


def get_all_cards() -> Dict[str, List[str]]:
    """
    Obtém todas as cartas armazenadas.
    
    Returns:
        Dicionário com todas as cartas (uuid -> cartas)
    """
    return ROUND_CARDS.copy()


def clear_registry() -> None:
    """Limpa o registro de cartas (deve ser chamado entre rounds)."""
    ROUND_CARDS.clear()


def has_cards(player_uuid: str) -> bool:
    """
    Verifica se um jogador tem cartas armazenadas.
    
    Args:
        player_uuid: UUID do jogador
    
    Returns:
        True se o jogador tem cartas armazenadas
    """
    return player_uuid in ROUND_CARDS and ROUND_CARDS[player_uuid] is not None


def remove_player_cards(player_uuid: str) -> None:
    """
    Remove as cartas de um jogador do registro.
    Usado quando um jogador dá fold - suas cartas não devem ser mostradas no resultado.
    
    Args:
        player_uuid: UUID do jogador
    """
    if player_uuid in ROUND_CARDS:
        del ROUND_CARDS[player_uuid]

