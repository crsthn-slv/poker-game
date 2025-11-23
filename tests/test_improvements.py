"""
Testes para as melhorias implementadas:
- Enums HandType e HandStrengthLevel
- Funções de validação
- Type hints
- Tratamento de erros padronizado
"""

import unittest
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from players.constants import HandType, HandStrengthLevel
from players.hand_utils import (
    validate_hole_cards,
    validate_community_cards,
    score_to_hand_name,
    score_to_strength_level,
    score_to_strength_level_heuristic,
    normalize_hole_cards,
    get_community_cards,
)
from players.hand_evaluator import HandEvaluator


class TestEnums(unittest.TestCase):
    """Testa os enums HandType e HandStrengthLevel."""
    
    def test_hand_type_values(self):
        """Testa se os valores dos enums HandType estão corretos."""
        self.assertEqual(HandType.ROYAL_FLUSH.value, "Royal Flush")
        self.assertEqual(HandType.STRAIGHT_FLUSH.value, "Straight Flush")
        self.assertEqual(HandType.FOUR_OF_A_KIND.value, "Four of a Kind")
        self.assertEqual(HandType.FULL_HOUSE.value, "Full House")
        self.assertEqual(HandType.FLUSH.value, "Flush")
        self.assertEqual(HandType.STRAIGHT.value, "Straight")
        self.assertEqual(HandType.THREE_OF_A_KIND.value, "Three of a Kind")
        self.assertEqual(HandType.TWO_PAIR.value, "Two Pair")
        self.assertEqual(HandType.ONE_PAIR.value, "One Pair")
        self.assertEqual(HandType.HIGH_CARD.value, "High Card")
    
    def test_hand_strength_level_values(self):
        """Testa se os valores dos enums HandStrengthLevel estão corretos."""
        self.assertEqual(HandStrengthLevel.EXCELLENT.value, "Excellent")
        self.assertEqual(HandStrengthLevel.GOOD.value, "Good")
        self.assertEqual(HandStrengthLevel.FAIR.value, "Fair")
        self.assertEqual(HandStrengthLevel.POOR.value, "Poor")


class TestValidationFunctions(unittest.TestCase):
    """Testa as funções de validação."""
    
    def test_validate_hole_cards_valid(self):
        """Testa validação de hole_cards válidos."""
        self.assertTrue(validate_hole_cards(['SA', 'HK']))
        self.assertTrue(validate_hole_cards(['D2', 'C3']))
        self.assertTrue(validate_hole_cards(['HQ', 'SK']))
    
    def test_validate_hole_cards_invalid(self):
        """Testa validação de hole_cards inválidos."""
        self.assertFalse(validate_hole_cards(None))
        self.assertFalse(validate_hole_cards([]))
        self.assertFalse(validate_hole_cards(['SA']))  # Apenas 1 carta
        self.assertFalse(validate_hole_cards(['INVALID']))  # Formato inválido
        self.assertFalse(validate_hole_cards(['XX', 'YY']))  # Cartas inválidas
        self.assertFalse(validate_hole_cards(['SA', 'HK', 'DQ']))  # Mais de 2 cartas
    
    def test_validate_community_cards_valid(self):
        """Testa validação de community_cards válidos."""
        self.assertTrue(validate_community_cards([]))  # Lista vazia é válida
        self.assertTrue(validate_community_cards(None))  # None é válido
        self.assertTrue(validate_community_cards(['SA', 'HK', 'DQ']))
        self.assertTrue(validate_community_cards(['D2', 'C3', 'S4', 'H5', 'C6']))  # 5 cartas
    
    def test_validate_community_cards_invalid(self):
        """Testa validação de community_cards inválidos."""
        self.assertFalse(validate_community_cards(['INVALID']))
        self.assertFalse(validate_community_cards(['XX', 'YY']))
        self.assertFalse(validate_community_cards(['SA', 'HK', 'DQ', 'C2', 'S3', 'H4']))  # Mais de 5 cartas


class TestHandUtilsWithEnums(unittest.TestCase):
    """Testa se as funções usam os enums corretamente."""
    
    def test_score_to_hand_name_uses_enum(self):
        """Testa se score_to_hand_name retorna valores do enum HandType."""
        self.assertEqual(score_to_hand_name(1), HandType.ROYAL_FLUSH.value)
        self.assertEqual(score_to_hand_name(5), HandType.STRAIGHT_FLUSH.value)
        self.assertEqual(score_to_hand_name(100), HandType.FOUR_OF_A_KIND.value)
        self.assertEqual(score_to_hand_name(5000), HandType.ONE_PAIR.value)
        self.assertEqual(score_to_hand_name(7000), HandType.HIGH_CARD.value)
    
    def test_score_to_strength_level_uses_enum(self):
        """Testa se score_to_strength_level retorna valores do enum HandStrengthLevel."""
        self.assertEqual(score_to_strength_level(1), HandStrengthLevel.EXCELLENT.value)
        self.assertEqual(score_to_strength_level(200), HandStrengthLevel.GOOD.value)
        self.assertEqual(score_to_strength_level(3000), HandStrengthLevel.FAIR.value)
        self.assertEqual(score_to_strength_level(5000), HandStrengthLevel.POOR.value)
    
    def test_score_to_strength_level_heuristic_uses_enum(self):
        """Testa se score_to_strength_level_heuristic retorna valores do enum."""
        self.assertEqual(score_to_strength_level_heuristic(80), HandStrengthLevel.EXCELLENT.value)
        self.assertEqual(score_to_strength_level_heuristic(60), HandStrengthLevel.GOOD.value)
        self.assertEqual(score_to_strength_level_heuristic(40), HandStrengthLevel.FAIR.value)
        self.assertEqual(score_to_strength_level_heuristic(20), HandStrengthLevel.POOR.value)


class TestHandEvaluatorTypeHints(unittest.TestCase):
    """Testa se HandEvaluator funciona corretamente com type hints."""
    
    def setUp(self):
        """Configura o evaluator para os testes."""
        self.evaluator = HandEvaluator()
    
    def test_pypoker_to_pokerkit_valid(self):
        """Testa conversão válida de cartas."""
        self.assertEqual(self.evaluator.pypoker_to_pokerkit('SA'), 'As')
        self.assertEqual(self.evaluator.pypoker_to_pokerkit('HK'), 'Kh')
        self.assertEqual(self.evaluator.pypoker_to_pokerkit('D2'), '2d')
        self.assertEqual(self.evaluator.pypoker_to_pokerkit('CQ'), 'Qc')
    
    def test_pypoker_to_pokerkit_invalid(self):
        """Testa conversão inválida retorna None."""
        self.assertIsNone(self.evaluator.pypoker_to_pokerkit(''))
        self.assertIsNone(self.evaluator.pypoker_to_pokerkit('X'))
        self.assertIsNone(self.evaluator.pypoker_to_pokerkit('INVALID'))
        self.assertIsNone(self.evaluator.pypoker_to_pokerkit('XX'))
    
    def test_evaluate_valid_hand(self):
        """Testa avaliação de mão válida."""
        hole_cards = ['SA', 'SK']
        community_cards = ['HQ', 'HJ', 'HT']
        score = self.evaluator.evaluate(hole_cards, community_cards)
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 0)
    
    def test_evaluate_invalid_hand(self):
        """Testa avaliação de mão inválida retorna valor padrão."""
        from players.constants import POKERKIT_MAX_SCORE
        
        # Mão inválida (menos de 2 cartas)
        score = self.evaluator.evaluate(['SA'], [])
        self.assertEqual(score, POKERKIT_MAX_SCORE)
        
        # Mão inválida (None)
        score = self.evaluator.evaluate(None, [])
        self.assertEqual(score, POKERKIT_MAX_SCORE)
    
    def test_compare_hands(self):
        """Testa comparação de mãos."""
        # hand1 melhor (menor score)
        result = self.evaluator.compare_hands(100, 200)
        self.assertEqual(result, -1)
        
        # hand2 melhor
        result = self.evaluator.compare_hands(200, 100)
        self.assertEqual(result, 1)
        
        # Empate
        result = self.evaluator.compare_hands(100, 100)
        self.assertEqual(result, 0)


class TestNormalizeFunctions(unittest.TestCase):
    """Testa funções de normalização."""
    
    def test_normalize_hole_cards_list(self):
        """Testa normalização de lista."""
        result = normalize_hole_cards(['SA', 'HK'])
        self.assertEqual(result, ['SA', 'HK'])
    
    def test_normalize_hole_cards_string(self):
        """Testa normalização de string."""
        result = normalize_hole_cards('SA')
        self.assertEqual(result, ['SA'])
    
    def test_normalize_hole_cards_none(self):
        """Testa normalização de None."""
        result = normalize_hole_cards(None)
        self.assertEqual(result, [])
    
    def test_get_community_cards_valid(self):
        """Testa extração de community_cards válida."""
        round_state = {'community_card': ['SA', 'HK', 'DQ']}
        result = get_community_cards(round_state)
        self.assertEqual(result, ['SA', 'HK', 'DQ'])
    
    def test_get_community_cards_empty(self):
        """Testa extração de community_cards vazia."""
        round_state = {'community_card': []}
        result = get_community_cards(round_state)
        self.assertEqual(result, [])
    
    def test_get_community_cards_none(self):
        """Testa extração quando não há community_cards."""
        round_state = {}
        result = get_community_cards(round_state)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()

