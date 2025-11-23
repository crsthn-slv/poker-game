"""
Hand Evaluator usando PokerKit para avaliação rápida de mãos de poker.
Substitui a função lenta _calc_hand_info_flg do PyPokerEngine.
"""

import sys
import os
from typing import List, Optional, Dict
from functools import lru_cache

# Garante que o site-packages está no path para encontrar pokerkit
try:
    import site
    site_packages = site.getsitepackages()
    for sp in site_packages:
        if sp not in sys.path:
            sys.path.insert(0, sp)
except:
    pass

# Tenta importar pokerkit de várias formas
StandardHighHand = None
_pokerkit_imported = False

try:
    from pokerkit import StandardHighHand
    _pokerkit_imported = True
    import os
    if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
        print(f"[DEBUG] hand_evaluator: Primeira tentativa de importação bem-sucedida")
except ImportError as e:
    # Log para debug
    import os
    if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
        print(f"[DEBUG] hand_evaluator: Primeira tentativa de importação falhou: {e}")
    
    # Tenta adicionar caminhos comuns do site-packages
    try:
        import site
        site_packages = site.getsitepackages()
        
        # Adiciona todos os site-packages encontrados
        for path in site_packages:
            pokerkit_path = os.path.join(path, 'pokerkit')
            if os.path.exists(pokerkit_path) and path not in sys.path:
                sys.path.insert(0, path)
                if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                    print(f"[DEBUG] hand_evaluator: Adicionado {path} ao sys.path")
        
        # Tenta importar novamente
        from pokerkit import StandardHighHand
        _pokerkit_imported = True
        if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
            print(f"[DEBUG] hand_evaluator: Segunda tentativa de importação bem-sucedida")
    except ImportError:
        # Tenta caminhos específicos do macOS/Homebrew
        try:
            import platform
            if platform.system() == 'Darwin':  # macOS
                # Caminhos comuns do Homebrew Python
                homebrew_paths = [
                    '/opt/homebrew/lib/python3.11/site-packages',
                    '/opt/homebrew/lib/python3.10/site-packages',
                    '/opt/homebrew/lib/python3.9/site-packages',
                    '/usr/local/lib/python3.11/site-packages',
                    '/usr/local/lib/python3.10/site-packages',
                    '/usr/local/lib/python3.9/site-packages',
                ]
                
                for path in homebrew_paths:
                    pokerkit_path = os.path.join(path, 'pokerkit')
                    if os.path.exists(pokerkit_path) and path not in sys.path:
                        sys.path.insert(0, path)
                        if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                            print(f"[DEBUG] hand_evaluator: Adicionado caminho Homebrew {path} ao sys.path")
                        break
                
                # Tenta importar novamente
                from pokerkit import StandardHighHand
                _pokerkit_imported = True
                if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                    print(f"[DEBUG] hand_evaluator: Importação bem-sucedida via caminho Homebrew")
            else:
                raise
        except ImportError as e2:
            # Se ainda falhar, não quebra o módulo - apenas marca como não disponível
            StandardHighHand = None
            _pokerkit_imported = False
            if os.environ.get('POKER_DEBUG', 'false').lower() == 'true':
                print(f"[DEBUG] hand_evaluator: Todas as tentativas de importação falharam: {e2}")
                print(f"[DEBUG] hand_evaluator: Módulo será carregado, mas pokerkit não estará disponível")
                import traceback
                traceback.print_exc()

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
        # Verifica se pokerkit está disponível
        if StandardHighHand is None:
            # Retorna valor padrão se pokerkit não estiver disponível
            return POKERKIT_MAX_SCORE
        
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
