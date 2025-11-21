"""
Utilitários compartilhados para avaliação de mão.
Evita duplicação de código entre players.
"""

def get_rank_value(rank):
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


def evaluate_hand_strength(hole_card, community_cards=None):
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

