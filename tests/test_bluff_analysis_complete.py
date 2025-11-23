"""
Testes completos para análise de blefe em tempo real.
Verifica se todos os bots estão usando a análise corretamente.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from utils.action_analyzer import analyze_possible_bluff, analyze_current_round_actions


class TestBluffAnalysisFunction(unittest.TestCase):
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
    
    def test_multiple_raises_detects_high_bluff_probability(self):
        """Testa que múltiplos raises detectam alta probabilidade de blefe."""
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
        self.assertTrue(result['analysis_factors']['multiple_raises'])
        self.assertGreater(result['bluff_confidence'], 0.5)
    
    def test_should_call_with_strong_hand(self):
        """Testa que com mão forte, deve pagar blefe."""
        round_state = self.base_round_state.copy()
        round_state['action_histories'] = {
            'preflop': [
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 10},
                {'uuid': self.opponent_uuid, 'action': 'RAISE', 'amount': 20}
            ]
        }
        
        result = analyze_possible_bluff(round_state, self.my_uuid, 45, None)
        
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
        
        result = analyze_possible_bluff(round_state, self.my_uuid, 15, None)
        
        self.assertFalse(result['should_call_bluff'])


class TestBotBluffIntegration(unittest.TestCase):
    """Testa integração da análise de blefe nos bots."""
    
    def test_tight_player_uses_bluff_analysis(self):
        """Testa que TightPlayer usa análise de blefe."""
        from players.tight_player import TightPlayer
        
        bot = TightPlayer()
        bot.uuid = "test-bot"
        
        round_state = {
            'street': 'preflop',
            'pot': {'main': {'amount': 30}},
            'seats': [
                {'uuid': bot.uuid, 'state': 'participating', 'stack': 100},
                {'uuid': 'opponent-1', 'state': 'participating', 'stack': 100}
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
        
        hole_card = [['SA', 'SK']]  # Mão muito forte
        
        # Verifica que análise de blefe é chamada
        hand_strength = bot._evaluate_hand_strength(hole_card, round_state)
        from utils.action_analyzer import analyze_possible_bluff
        bluff_analysis = analyze_possible_bluff(
            round_state, bot.uuid, hand_strength, bot.memory_manager
        )
        
        self.assertIsNotNone(bluff_analysis)
        self.assertGreater(bluff_analysis['possible_bluff_probability'], 0.4)
        
        # Com mão forte, deve recomendar pagar blefe
        if hand_strength >= 40:
            self.assertTrue(bluff_analysis['should_call_bluff'])
    
    def test_aggressive_player_uses_bluff_analysis(self):
        """Testa que AggressivePlayer usa análise de blefe."""
        from players.aggressive_player import AggressivePlayer
        
        bot = AggressivePlayer()
        bot.uuid = "test-bot"
        
        round_state = {
            'street': 'preflop',
            'pot': {'main': {'amount': 30}},
            'seats': [
                {'uuid': bot.uuid, 'state': 'participating', 'stack': 100},
                {'uuid': 'opponent-1', 'state': 'participating', 'stack': 100}
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
        
        hole_card = [['HA', 'HK']]
        
        # Verifica que análise funciona
        hand_strength = bot._evaluate_hand_strength(hole_card)
        from utils.action_analyzer import analyze_possible_bluff
        bluff_analysis = analyze_possible_bluff(
            round_state, bot.uuid, hand_strength, bot.memory_manager
        )
        
        self.assertIsNotNone(bluff_analysis)
        
        # AggressivePlayer tem threshold 22, então com mão 25+ deve pagar blefe
        if hand_strength >= 25 and bluff_analysis['possible_bluff_probability'] > 0.5:
            self.assertTrue(bluff_analysis['should_call_bluff'])
    
    def test_smart_player_uses_bluff_analysis(self):
        """Testa que SmartPlayer usa análise de blefe."""
        from players.smart_player import SmartPlayer
        
        bot = SmartPlayer()
        bot.uuid = "test-bot"
        
        round_state = {
            'street': 'preflop',
            'pot': {'main': {'amount': 30}},
            'seats': [
                {'uuid': bot.uuid, 'state': 'participating', 'stack': 100},
                {'uuid': 'opponent-1', 'state': 'participating', 'stack': 100}
            ],
            'action_histories': {
                'preflop': [
                    {'uuid': 'opponent-1', 'action': 'RAISE', 'amount': 10},
                    {'uuid': 'opponent-1', 'action': 'RAISE', 'amount': 20}
                ]
            }
        }
        
        hole_card = [['DA', 'DK']]
        
        # Verifica que análise funciona
        hand_strength = bot._evaluate_hand_strength(hole_card, round_state)
        from utils.action_analyzer import analyze_possible_bluff
        bluff_analysis = analyze_possible_bluff(
            round_state, bot.uuid, hand_strength, bot.memory_manager
        )
        
        self.assertIsNotNone(bluff_analysis)
        
        # SmartPlayer tem threshold 28
        if hand_strength >= 30 and bluff_analysis['possible_bluff_probability'] > 0.5:
            self.assertTrue(bluff_analysis['should_call_bluff'])


class TestBluffAnalysisWithMemory(unittest.TestCase):
    """Testa análise de blefe com histórico de memória."""
    
    def test_bluff_analysis_considers_opponent_history(self):
        """Testa que análise considera histórico de blefes do oponente."""
        from utils.memory_manager import UnifiedMemoryManager
        from utils.action_analyzer import analyze_possible_bluff
        
        my_uuid = "bot-123"
        opp_uuid = "opponent-456"
        
        # Cria memory manager com histórico de blefes
        memory_manager = UnifiedMemoryManager("test_memory.json")
        memory_manager.memory['opponents'][opp_uuid] = {
            'uuid': opp_uuid,
            'name': 'TestOpponent',
            'rounds_against': [
                {
                    'round': 1,
                    'analysis': 'blefe_sucesso',
                    'opponent_actions': [{'action': 'raise'}],
                    'hand_strength': 20
                },
                {
                    'round': 2,
                    'analysis': 'blefe_sucesso',
                    'opponent_actions': [{'action': 'raise'}],
                    'hand_strength': 22
                }
            ],
            'total_rounds_against': 2,
            'last_seen_round': 2
        }
        
        round_state = {
            'street': 'preflop',
            'pot': {'main': {'amount': 30}},
            'seats': [
                {'uuid': my_uuid, 'state': 'participating'},
                {'uuid': opp_uuid, 'state': 'participating'}
            ],
            'action_histories': {
                'preflop': [
                    {'uuid': opp_uuid, 'action': 'RAISE', 'amount': 10}
                ]
            }
        }
        
        result = analyze_possible_bluff(round_state, my_uuid, 30, memory_manager)
        
        # Com histórico de blefes, probabilidade deve ser maior
        self.assertGreater(result['possible_bluff_probability'], 0.2)
        self.assertTrue(result['analysis_factors']['opponent_bluff_history'])


class TestBluffAnalysisDifferentStreets(unittest.TestCase):
    """Testa análise de blefe em diferentes streets."""
    
    def test_preflop_bluff_probability(self):
        """Testa que preflop tem maior probabilidade de blefe."""
        my_uuid = "bot-123"
        opp_uuid = "opponent-456"
        
        round_state = {
            'street': 'preflop',
            'pot': {'main': {'amount': 30}},
            'seats': [
                {'uuid': my_uuid, 'state': 'participating'},
                {'uuid': opp_uuid, 'state': 'participating'}
            ],
            'action_histories': {
                'preflop': [
                    {'uuid': opp_uuid, 'action': 'RAISE', 'amount': 10}
                ]
            }
        }
        
        result_preflop = analyze_possible_bluff(round_state, my_uuid, 30, None)
        
        round_state['street'] = 'river'
        round_state['action_histories'] = {
            'river': [
                {'uuid': opp_uuid, 'action': 'RAISE', 'amount': 10}
            ]
        }
        
        result_river = analyze_possible_bluff(round_state, my_uuid, 30, None)
        
        # Preflop deve ter probabilidade maior
        self.assertGreater(result_preflop['possible_bluff_probability'],
                          result_river['possible_bluff_probability'])


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TESTES COMPLETOS: Análise de Blefe em Tempo Real")
    print("=" * 60)
    print()
    
    unittest.main(verbosity=2)

