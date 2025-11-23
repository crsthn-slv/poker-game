"""
Hand Evaluator usando PokerKit para avaliação rápida de mãos de poker.
Substitui a função lenta _calc_hand_info_flg do PyPokerEngine.
"""

from typing import List, Optional, Dict
from functools import lru_cache
from pokerkit import StandardHighHand
from .constants import POKERKIT_MAX_SCORE

# Mapeamentos constantes para conversão
_RANK_MAP = {
    '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7',
    '8': '8', '9': '9', 'T': 'T', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'
}

_SUIT_MAP = {
    'S': 's',  # Spades
    'H': 'h',  # Hearts
    'D': 'd',  # Diamonds
    'C': 'c'   # Clubs
}


@lru_cache(maxsize=128)
def _pypoker_to_pokerkit_cached(card_str: str) -> Optional[str]:
    """
    Função auxiliar com cache para conversão de cartas.
    Cache compartilhado entre todas as instâncias de HandEvaluator.
    """
    if not card_str or len(card_str) < 2:
        return None
    
    # PyPokerEngine: primeiro caractere é suit, resto é rank
    suit_char = card_str[0].upper()
    rank_str = card_str[1:].upper()
    
    # Converte suit para lowercase (PokerKit usa lowercase)
    pokerkit_suit = _SUIT_MAP.get(suit_char)
    if not pokerkit_suit:
        return None
    
    # Valida rank
    pokerkit_rank = _RANK_MAP.get(rank_str)
    if not pokerkit_rank:
        return None
    
    # Cria string no formato PokerKit: 'As', 'Kh', '2c', etc.
    pokerkit_card_str = pokerkit_rank + pokerkit_suit
    return pokerkit_card_str


class HandEvaluator:
    """
    Wrapper para avaliação de mãos usando PokerKit.
    Converte formato de cartas do PyPokerEngine (ex: 'SA', 'HK') para formato PokerKit.
    """
    
    def __init__(self):
        # Mapeamentos agora são constantes globais para permitir cache compartilhado
        pass
    
    def pypoker_to_pokerkit(self, card_str: str) -> Optional[str]:
        """
        Converte uma carta do formato PyPokerEngine para formato PokerKit.
        Otimizado com cache LRU compartilhado para melhor performance.
        
        Args:
            card_str: String no formato PyPokerEngine (ex: 'SA', 'HK', 'D2')
        
        Returns:
            String no formato PokerKit (ex: 'As', 'Kh', '2d'), ou None se inválido
        """
        return _pypoker_to_pokerkit_cached(card_str)
    
    def evaluate(
        self, 
        hole_cards: List[str], 
        community_cards: Optional[List[str]] = None
    ) -> int:
        """
        Avalia uma mão de poker usando PokerKit.
        
        Args:
            hole_cards: Lista de cartas do jogador no formato PyPokerEngine (ex: ['SA', 'HK'])
            community_cards: Lista de cartas comunitárias no formato PyPokerEngine (ex: ['D2', 'C3', 'S4'])
        
        Returns:
            Int representando o rank da mão (menor = melhor mão, compatível com formato anterior)
        """
        if not hole_cards or len(hole_cards) < 2:
            # Mão inválida - retorna valor alto (pior mão possível)
            return POKERKIT_MAX_SCORE
        
        # Converte cartas do jogador
        hand = []
        for card_str in hole_cards[:2]:  # Apenas 2 cartas do jogador
            pokerkit_card = self.pypoker_to_pokerkit(card_str)
            if pokerkit_card is not None:
                hand.append(pokerkit_card)
        
        if len(hand) < 2:
            return POKERKIT_MAX_SCORE  # Mão inválida
        
        # Converte cartas comunitárias
        board = []
        if community_cards:
            for card_str in community_cards:
                pokerkit_card = self.pypoker_to_pokerkit(card_str)
                if pokerkit_card is not None:
                    board.append(pokerkit_card)
        
        try:
            # Combina hole cards em uma string para PokerKit
            hole_str = ''.join(hand)
            board_str = ''.join(board) if board else ''
            
            # PokerKit StandardHighHand.from_game() cria uma mão a partir de hole cards e board
            # Retorna um objeto Hand com entry.index (menor index = melhor mão)
            hand_obj = StandardHighHand.from_game(hole_str, board_str)
            
            # Retorna o index da mão invertido (menor = melhor, compatível com formato anterior)
            # PokerKit usa maior index = melhor mão (7461 = Royal Flush, 0 = pior mão)
            # Invertemos para manter compatibilidade: menor = melhor (0 = Royal Flush, 7461 = pior)
            return POKERKIT_MAX_SCORE - hand_obj.entry.index
        except (ValueError, TypeError, AttributeError) as e:
            # Padronização: erros de validação/entrada retornam None implicitamente
            # mas como precisamos retornar int, retornamos valor de erro padrão
            # Log apenas em modo debug para não poluir output
            import os
            if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                print(f"[HandEvaluator] Erro ao avaliar mão: {e}")
            return POKERKIT_MAX_SCORE  # Retorna pior mão possível em caso de erro
        except Exception as e:
            # Erros inesperados: log e retorna valor padrão
            import os
            if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                print(f"[HandEvaluator] Erro inesperado ao avaliar mão: {e}")
            return POKERKIT_MAX_SCORE  # Retorna pior mão possível em caso de erro
    
    def compare_hands(self, hand1_score: int, hand2_score: int) -> int:
        """
        Compara duas mãos baseado nos scores do PokerKit.
        
        Args:
            hand1_score: Score da primeira mão (do PokerKit)
            hand2_score: Score da segunda mão (do PokerKit)
        
        Returns:
            -1 se hand1 é melhor, 1 se hand2 é melhor, 0 se empate
        """
        if hand1_score < hand2_score:
            return -1  # hand1 é melhor (menor score = melhor mão)
        elif hand1_score > hand2_score:
            return 1   # hand2 é melhor
        else:
            return 0   # Empate
    
    def get_hand_rank(
        self, 
        hole_cards: List[str], 
        community_cards: Optional[List[str]] = None
    ) -> int:
        """
        Retorna o rank numérico da mão (compatível com PyPokerEngine).
        
        Args:
            hole_cards: Lista de cartas do jogador
            community_cards: Lista de cartas comunitárias
        
        Returns:
            Int representando o rank da mão
        """
        return self.evaluate(hole_cards, community_cards)
