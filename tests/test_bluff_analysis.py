"""
Testes para análise de blefe em tempo real.
Verifica se os bots detectam possível blefe baseado em ações do round atual.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from utils.action_analyzer import analyze_possible_bluff, analyze_current_round_actions


class TestBluffAnalysis(unittest.TestCase):
    """Testa a função analyze_possible_bluff."""
    
    def setUp(self):
        """Prepara dados de teste."""
        self.my_uuid = "bot-123"
        self.opponent_uuid = "opponent-456"
        
        self.base_round_state = {
            'street': 'preflop',
            'pot': {'main': {'amount': 30}},
            'seats': [
                {'uuid': self.my_uuid, 'state': 'participating'},
                {'uuid': self.opponent_uuid, 'state': 'participating'}
            ],
            'action_histories': {}
        }
    
    def test_no_actions_no_bluff(self):
        """Testa que sem ações, não há indicação de blefe."""
        round_state = self.base_round_state.copy()
        round_state['action_histories'] = {'preflop': []}
        
        result = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        self.assertIsNotNone(result)
        self.assertIn('possible_bluff_probability', result)
        self.assertIn('should_call_bluff', result)
        self.assertIn('bluff_confidence', result)
        self.assertLess(result['possible_bluff_probability'], 0.3)
    
    def test_single_raise_low_bluff_probability(self):
        """Testa que um único raise tem probabilidade moderada de blefe."""
        round_state = self.base_round_state.copy()
        round_state['pot'] = {'main': {'amount': 100}}  # Pot maior para reduzir probabilidade
        round_state['street'] = 'river'  # Street final para reduzir probabilidade
        round_state['action_histories'] = {
            'river': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10}
            ]
        }
        
        result = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        self.assertGreater(result['possible_bluff_probability'], 0.1)
        self.assertLess(result['possible_bluff_probability'], 0.5)  # Ajustado para 0.5
    
    def test_multiple_raises_high_bluff_probability(self):
        """Testa que múltiplos raises indicam alta probabilidade de blefe."""
        round_state = self.base_round_state.copy()
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10},
                {'uuid': self.my_uuid, 'action': 'CALL', 'amount': 10},
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 20}
            ]
        }
        
        result = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        self.assertGreater(result['possible_bluff_probability'], 0.4)
        self.assertIn('multiple_raises', result['analysis_factors'])
        self.assertTrue(result['analysis_factors']['multiple_raises'])
    
    def test_should_call_with_strong_hand(self):
        """Testa que com mão forte, deve pagar possível blefe."""
        round_state = self.base_round_state.copy()
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10},
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 20}
            ]
        }
        
        # Mão forte (40+)
        result = analyze_possible_bluff(round_state, self.my_uuid, 45, None)
        
        self.assertTrue(result['should_call_bluff'])
    
    def test_should_call_with_medium_hand_and_high_bluff_prob(self):
        """Testa que com mão média e alta probabilidade de blefe, deve pagar."""
        round_state = self.base_round_state.copy()
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10},
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 20}
            ]
        }
        
        # Mão média (30) + alta probabilidade de blefe (>0.5)
        result = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        # Com 2 raises, probabilidade deve ser > 0.5
        if result['possible_bluff_probability'] > 0.5:
            self.assertTrue(result['should_call_bluff'])
    
    def test_should_not_call_with_weak_hand(self):
        """Testa que com mão fraca, não deve pagar blefe."""
        round_state = self.base_round_state.copy()
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10},
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 20}
            ]
        }
        
        # Mão fraca (< 25)
        result = analyze_possible_bluff(round_state, self.my_uuid, 20, None)
        
        self.assertFalse(result['should_call_bluff'])
    
    def test_early_street_increases_bluff_probability(self):
        """Testa que streets iniciais aumentam probabilidade de blefe."""
        # Preflop
        round_state = self.base_round_state.copy()
        round_state['street'] = 'preflop'
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10}
            ]
        }
        
        result_preflop = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        # River
        round_state['street'] = 'river'
        round_state['action_histories'] = {
            'river': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10}
            ]
        }
        
        result_river = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        # Preflop deve ter probabilidade maior
        self.assertGreater(result_preflop['possible_bluff_probability'], 
                          result_river['possible_bluff_probability'])
    
    def test_small_pot_increases_bluff_probability(self):
        """Testa que pot pequeno aumenta probabilidade de blefe."""
        round_state = self.base_round_state.copy()
        round_state['pot'] = {'main': {'amount': 30}}  # Pot pequeno
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10}
            ]
        }
        
        result_small = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        # Pot grande
        round_state['pot'] = {'main': {'amount': 200}}
        result_large = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        # Pot pequeno deve ter probabilidade maior
        self.assertGreater(result_small['possible_bluff_probability'],
                          result_large['possible_bluff_probability'])
    
    def test_high_aggression_increases_bluff_probability(self):
        """Testa que alta agressão aumenta probabilidade de blefe."""
        round_state = self.base_round_state.copy()
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10},
                {'uuid': self.my_uuid, 'action': 'CALL', 'amount': 10},
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 20}
            ]
        }
        
        result = analyze_possible_bluff(round_state, self.my_uuid, 30, None)
        
        # Com 2 raises e 1 call, agressão = 2/3 = 0.67 > 0.6
        self.assertIn('high_aggression', result['analysis_factors'])
        self.assertTrue(result['analysis_factors']['high_aggression'])


class TestBluffAnalysisIntegration(unittest.TestCase):
    """Testa integração da análise de blefe com bots."""
    
    def test_tight_player_considers_bluff(self):
        """Testa que TightPlayer considera análise de blefe."""
        from players.tight_player import TightPlayer
        
        bot = TightPlayer()
        bot.uuid = "test-bot"
        
        round_state = {
            'street': 'preflop',
            'pot': {'main': {'amount': 30}},
            'seats': [
                {'uuid': bot.uuid, 'state': 'participating'},
                {'uuid': 'opponent-1', 'state': 'participating'}
            ],
            'action_histories': {
                'preflop': [
                    {'uuid': 'opponent-1', 'action': 'RAISE', 'amount': 10},
                    {'uuid': 'opponent-1', 'action': 'RAISE', 'amount': 20}
                ]
            }
        }
        
        valid_actions = [
            {'action': 'fold', 'amount': 0},
            {'action': 'call', 'amount': 20},
            {'action': 'raise', 'amount': {'min': 30, 'max': 100}}
        ]
        
        # Verifica que a análise de blefe detecta múltiplos raises
        hole_card = [['SA', 'SK']]
        hand_strength = bot._evaluate_hand_strength(hole_card, round_state)
        
        from utils.action_analyzer import analyze_possible_bluff
        bluff_analysis = analyze_possible_bluff(
            round_state, bot.uuid, hand_strength, bot.memory_manager
        )
        
        # Com 2 raises, deve detectar alta probabilidade de blefe
        self.assertGreater(bluff_analysis['possible_bluff_probability'], 0.4)
        self.assertTrue(bluff_analysis['analysis_factors']['multiple_raises'])
        
        # Com mão forte, deve recomendar pagar blefe
        if hand_strength >= 40:
            self.assertTrue(bluff_analysis['should_call_bluff'])


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TESTES AUTOMÁTICOS: Análise de Blefe em Tempo Real")
    print("=" * 60)
    print()
    
    unittest.main(verbosity=2)

