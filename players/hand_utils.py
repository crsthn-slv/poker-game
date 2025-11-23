"""
Utilitários compartilhados para avaliação de mão.
Evita duplicação de código entre players.
"""

from typing import List, Optional, Union, Dict, Any
from .constants import (
    POKERKIT_MAX_SCORE,
    HAND_SCORE_ROYAL_FLUSH_MAX,
    HAND_SCORE_STRAIGHT_FLUSH_MAX,
    HAND_SCORE_FOUR_OF_A_KIND_MAX,
    HAND_SCORE_FULL_HOUSE_MAX,
    HAND_SCORE_FLUSH_MAX,
    HAND_SCORE_STRAIGHT_MAX,
    HAND_SCORE_THREE_OF_A_KIND_MAX,
    HAND_SCORE_TWO_PAIR_MAX,
    HAND_SCORE_ONE_PAIR_MAX,
    HAND_STRENGTH_EXCELLENT_MAX,
    HAND_STRENGTH_GOOD_MAX,
    HAND_STRENGTH_FAIR_MAX,
    HandType,
    HandStrengthLevel,
)


def get_rank_value(rank: str) -> int:
    """Retorna valor numérico do rank da carta.
    
    Args:
        rank: Rank da carta ('2'-'9', 'T', 'J', 'Q', 'K', 'A')
    
    Returns:
        Valor numérico (2-14)
    """
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
        '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    return rank_map.get(rank, 0)


def evaluate_hand_strength(
    hole_card: List[str], 
    community_cards: Optional[List[str]] = None
) -> int:
    """Avalia a força básica das cartas do jogador.
    
    Args:
        hole_card: Lista de 2 cartas do jogador (ex: ['SA', 'SK'])
        community_cards: Lista opcional de cartas comunitárias
    
    Returns:
        Pontuação de força (0-100+)
        - Par: 50-62 (baseado no rank)
        - Duas cartas altas: 40-45
        - Uma carta alta: 25-30
        - Mesmo naipe: 15-20
        - Cartas baixas: 5-10
    """
    if not hole_card or len(hole_card) < 2:
        return 0
    
    card_ranks = [card[1] for card in hole_card]
    card_suits = [card[0] for card in hole_card]
    
    # Par nas mãos
    if card_ranks[0] == card_ranks[1]:
        rank_value = get_rank_value(card_ranks[0])
        base_strength = 50 + rank_value
        
        # Se há cartas comunitárias, verifica possibilidade de trinca ou melhor
        if community_cards:
            all_ranks = card_ranks + [c[1] for c in community_cards]
            rank_counts = {}
            for rank in all_ranks:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
            # Trinca
            if max(rank_counts.values()) >= 3:
                return 80
            # Dois pares
            pairs = [count for count in rank_counts.values() if count >= 2]
            if len(pairs) >= 2:
                return 70
        
        return base_strength
    
    # Cartas altas
    high_cards = ['A', 'K', 'Q', 'J']
    has_high = any(rank in high_cards for rank in card_ranks)
    
    if has_high:
        # Duas cartas altas
        if all(rank in high_cards for rank in card_ranks):
            return 45
        # Uma carta alta
        return 30
    
    # Mesmo naipe (possibilidade de flush)
    if card_suits[0] == card_suits[1]:
        if community_cards:
            same_suit_community = [c for c in community_cards if c[0] == card_suits[0]]
            if len(same_suit_community) >= 3:
                return 60  # Flush possível
        return 20
    
    # Cartas baixas
    return 10


# ============================================================================
# Funções Helper para Padronização de Nomenclaturas
# ============================================================================

def normalize_hole_cards(
    hole_card: Union[List[str], str, None]
) -> List[str]:
    """
    Normaliza hole_card (singular) para hole_cards (plural) padronizado.
    
    PyPokerEngine usa 'hole_card' (singular), mas internamente usamos
    'hole_cards' (plural) para consistência.
    
    Args:
        hole_card: Carta(s) do jogador (pode ser lista, string ou None)
    
    Returns:
        List[str]: Lista de 2 cartas padronizada, ou lista vazia se inválido
    """
    if hole_card is None:
        return []
    
    if isinstance(hole_card, list):
        # Já é uma lista, retorna como está (mas garante que tem 2 elementos)
        if len(hole_card) >= 2:
            return hole_card[:2]
        return []
    
    if isinstance(hole_card, str):
        # É uma string única, retorna como lista
        return [hole_card]
    
    return []


def get_community_cards(round_state: Dict[str, Any]) -> List[str]:
    """
    Extrai e padroniza cartas comunitárias do round_state.
    
    PyPokerEngine usa 'community_card' (singular) no round_state,
    mas internamente usamos 'community_cards' (plural) para consistência.
    
    Args:
        round_state: Estado do round do PyPokerEngine
    
    Returns:
        List[str]: Lista de cartas comunitárias (pode estar vazia)
    """
    if not round_state or not isinstance(round_state, dict):
        return []
    
    community_card = round_state.get('community_card', [])
    
    if not community_card:
        return []
    
    if isinstance(community_card, list):
        return community_card
    
    if isinstance(community_card, str):
        # Se for uma string única, retorna como lista
        return [community_card]
    
    return []


# ============================================================================
# Funções de Validação de Entrada
# ============================================================================

def validate_hole_cards(hole_cards: Union[List[str], str, None]) -> bool:
    """
    Valida se hole_cards está no formato correto.
    
    Args:
        hole_cards: Carta(s) do jogador (pode ser lista, string ou None)
    
    Returns:
        bool: True se válido, False caso contrário
    
    Examples:
        >>> validate_hole_cards(['SA', 'HK'])
        True
        >>> validate_hole_cards(['SA'])
        False
        >>> validate_hole_cards(None)
        False
        >>> validate_hole_cards(['INVALID'])
        False
    """
    if hole_cards is None:
        return False
    
    # Verifica tamanho original antes de normalizar
    if isinstance(hole_cards, list):
        if len(hole_cards) != 2:
            return False
    elif isinstance(hole_cards, str):
        # String única não é válida (precisa de 2 cartas)
        return False
    else:
        return False
    
    # Normaliza para lista
    normalized = normalize_hole_cards(hole_cards)
    
    # Deve ter exatamente 2 cartas
    if len(normalized) != 2:
        return False
    
    # Valida formato de cada carta (deve ter pelo menos 2 caracteres: suit + rank)
    valid_suits = {'S', 'H', 'D', 'C'}
    valid_ranks = {'2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'}
    
    for card in normalized:
        if not isinstance(card, str) or len(card) < 2:
            return False
        
        suit = card[0].upper()
        rank = card[1:].upper()
        
        if suit not in valid_suits or rank not in valid_ranks:
            return False
    
    return True


def validate_community_cards(community_cards: Union[List[str], str, None]) -> bool:
    """
    Valida se community_cards está no formato correto.
    
    Args:
        community_cards: Cartas comunitárias (pode ser lista, string ou None)
    
    Returns:
        bool: True se válido, False caso contrário
    
    Examples:
        >>> validate_community_cards(['SA', 'HK', 'DQ'])
        True
        >>> validate_community_cards([])
        True
        >>> validate_community_cards(['INVALID'])
        False
    """
    if community_cards is None:
        return True  # None é válido (pode não haver cartas comunitárias ainda)
    
    # Converte para lista se necessário
    if isinstance(community_cards, str):
        cards_list = [community_cards]
    elif isinstance(community_cards, list):
        cards_list = community_cards
    else:
        return False
    
    # Lista vazia é válida (preflop)
    if len(cards_list) == 0:
        return True
    
    # Valida formato de cada carta
    valid_suits = {'S', 'H', 'D', 'C'}
    valid_ranks = {'2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'}
    
    for card in cards_list:
        if not isinstance(card, str) or len(card) < 2:
            return False
        
        suit = card[0].upper()
        rank = card[1:].upper()
        
        if suit not in valid_suits or rank not in valid_ranks:
            return False
    
    # Máximo de 5 cartas comunitárias
    if len(cards_list) > 5:
        return False
    
    return True


# ============================================================================
# Funções Centralizadas de Mapeamento Score → Nome/Nível
# ============================================================================

def score_to_hand_name(score: int) -> str:
    """
    Converte score do PokerKit para nome da mão.
    
    Args:
        score: Score do PokerKit (0-POKERKIT_MAX_SCORE, menor = melhor)
    
    Returns:
        str: Nome da mão ('Royal Flush', 'One Pair', etc.)
    
    Examples:
        >>> score_to_hand_name(1)
        'Royal Flush'
        >>> score_to_hand_name(5000)
        'One Pair'
        >>> score_to_hand_name(7000)
        'High Card'
    """
    if score <= HAND_SCORE_ROYAL_FLUSH_MAX:
        return HandType.ROYAL_FLUSH.value
    elif score <= HAND_SCORE_STRAIGHT_FLUSH_MAX:
        return HandType.STRAIGHT_FLUSH.value
    elif score <= HAND_SCORE_FOUR_OF_A_KIND_MAX:
        return HandType.FOUR_OF_A_KIND.value
    elif score <= HAND_SCORE_FULL_HOUSE_MAX:
        return HandType.FULL_HOUSE.value
    elif score <= HAND_SCORE_FLUSH_MAX:
        return HandType.FLUSH.value
    elif score <= HAND_SCORE_STRAIGHT_MAX:
        return HandType.STRAIGHT.value
    elif score <= HAND_SCORE_THREE_OF_A_KIND_MAX:
        return HandType.THREE_OF_A_KIND.value
    elif score <= HAND_SCORE_TWO_PAIR_MAX:
        return HandType.TWO_PAIR.value
    elif score <= HAND_SCORE_ONE_PAIR_MAX:
        return HandType.ONE_PAIR.value
    else:
        return HandType.HIGH_CARD.value


def score_to_strength_level(score: int) -> str:
    """
    Converte score do PokerKit para nível semântico de força.
    
    Args:
        score: Score do PokerKit (0-POKERKIT_MAX_SCORE, menor = melhor)
    
    Returns:
        str: Nível semântico ('Excellent', 'Good', 'Fair', 'Poor')
    
    Examples:
        >>> score_to_strength_level(1)
        'Excellent'
        >>> score_to_strength_level(200)
        'Good'
        >>> score_to_strength_level(5000)
        'Poor'
    """
    if score <= HAND_STRENGTH_EXCELLENT_MAX:
        return HandStrengthLevel.EXCELLENT.value
    elif score <= HAND_STRENGTH_GOOD_MAX:
        return HandStrengthLevel.GOOD.value
    elif score <= HAND_STRENGTH_FAIR_MAX:
        return HandStrengthLevel.FAIR.value
    else:
        return HandStrengthLevel.POOR.value


def score_to_strength_level_heuristic(base_strength: int) -> str:
    """
    Converte score heurístico para nível semântico (usado no preflop).
    
    Args:
        base_strength: Score heurístico (0-100+)
    
    Returns:
        str: Nível semântico ('Excellent', 'Good', 'Fair', 'Poor')
    """
    if base_strength >= 70:
        return HandStrengthLevel.EXCELLENT.value
    elif base_strength >= 50:
        return HandStrengthLevel.GOOD.value
    elif base_strength >= 30:
        return HandStrengthLevel.FAIR.value
    else:
        return HandStrengthLevel.POOR.value

