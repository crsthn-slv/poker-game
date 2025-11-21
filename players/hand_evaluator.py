"""
Hand Evaluator usando treys para avaliação rápida de mãos de poker.
Substitui a função lenta _calc_hand_info_flg do PyPokerEngine.
"""

from treys import Card, Evaluator


class HandEvaluator:
    """
    Wrapper para avaliação de mãos usando treys.
    Converte formato de cartas do PyPokerEngine (ex: 'SA', 'HK') para formato treys.
    """
    
    def __init__(self):
        self.evaluator = Evaluator()
        
        # Mapeamento de rank: PyPokerEngine -> treys
        # PyPokerEngine usa: '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'
        # treys usa: '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'
        self.rank_map = {
            '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7',
            '8': '8', '9': '9', 'T': 'T', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'
        }
        
        # Mapeamento de suit: PyPokerEngine -> treys
        # PyPokerEngine usa: 'S' (Spades), 'H' (Hearts), 'D' (Diamonds), 'C' (Clubs)
        # treys usa: 's', 'h', 'd', 'c' (lowercase)
        self.suit_map = {
            'S': 's',  # Spades
            'H': 'h',  # Hearts
            'D': 'd',  # Diamonds
            'C': 'c'   # Clubs
        }
    
    def pypoker_to_treys(self, card_str):
        """
        Converte uma carta do formato PyPokerEngine para formato treys.
        
        Args:
            card_str: String no formato PyPokerEngine (ex: 'SA', 'HK', 'D2')
        
        Returns:
            Int representando a carta no formato treys, ou None se inválido
        """
        if not card_str or len(card_str) < 2:
            return None
        
        # PyPokerEngine: primeiro caractere é suit, resto é rank
        suit_char = card_str[0].upper()
        rank_str = card_str[1:].upper()
        
        # Converte suit para lowercase (treys usa lowercase)
        treys_suit = self.suit_map.get(suit_char)
        if not treys_suit:
            return None
        
        # Valida rank
        treys_rank = self.rank_map.get(rank_str)
        if not treys_rank:
            return None
        
        # Cria string no formato treys: 'As', 'Kh', '2c', etc.
        treys_card_str = treys_rank + treys_suit
        
        try:
            # treys.Card.new() aceita string no formato 'As', 'Kh', etc.
            return Card.new(treys_card_str)
        except Exception as e:
            print(f"[HandEvaluator] Erro ao converter carta {card_str} para treys: {e}")
            return None
    
    def evaluate(self, hole_cards, community_cards):
        """
        Avalia uma mão de poker usando treys.
        
        Args:
            hole_cards: Lista de cartas do jogador no formato PyPokerEngine (ex: ['SA', 'HK'])
            community_cards: Lista de cartas comunitárias no formato PyPokerEngine (ex: ['D2', 'C3', 'S4'])
        
        Returns:
            Int representando o rank da mão (menor = melhor mão, como treys)
        """
        if not hole_cards or len(hole_cards) < 2:
            # Mão inválida - retorna valor alto (pior mão possível)
            return 7462  # Valor máximo do treys
        
        # Converte cartas do jogador
        hand = []
        for card_str in hole_cards[:2]:  # Apenas 2 cartas do jogador
            treys_card = self.pypoker_to_treys(card_str)
            if treys_card is not None:
                hand.append(treys_card)
        
        if len(hand) < 2:
            return 7462  # Mão inválida
        
        # Converte cartas comunitárias
        board = []
        if community_cards:
            for card_str in community_cards:
                treys_card = self.pypoker_to_treys(card_str)
                if treys_card is not None:
                    board.append(treys_card)
        
        try:
            # Avalia a mão usando treys
            # treys retorna um valor onde menor = melhor mão
            score = self.evaluator.evaluate(board, hand)
            return score
        except Exception as e:
            print(f"[HandEvaluator] Erro ao avaliar mão: {e}")
            return 7462  # Retorna pior mão possível em caso de erro
    
    def compare_hands(self, hand1_score, hand2_score):
        """
        Compara duas mãos baseado nos scores do treys.
        
        Args:
            hand1_score: Score da primeira mão (do treys)
            hand2_score: Score da segunda mão (do treys)
        
        Returns:
            -1 se hand1 é melhor, 1 se hand2 é melhor, 0 se empate
        """
        if hand1_score < hand2_score:
            return -1  # hand1 é melhor (menor score = melhor mão)
        elif hand1_score > hand2_score:
            return 1   # hand2 é melhor
        else:
            return 0   # Empate
    
    def get_hand_rank(self, hole_cards, community_cards):
        """
        Retorna o rank numérico da mão (compatível com PyPokerEngine).
        
        Args:
            hole_cards: Lista de cartas do jogador
            community_cards: Lista de cartas comunitárias
        
        Returns:
            Int representando o rank da mão
        """
        return self.evaluate(hole_cards, community_cards)

