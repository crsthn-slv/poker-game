"""
Testes de fluxo completo do jogo para validar que não há erros de serialização.
Simula um round completo e verifica que todos os dados são serializados corretamente.
"""

import sys
import os
import unittest
import json
import threading
import time

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.server import WebPlayer, game_state, game_lock


class TestGameFlow(unittest.TestCase):
    """Testa o fluxo completo do jogo e serialização."""

    def setUp(self):
        """Prepara o ambiente de teste."""
        self.player = WebPlayer()
        # Limpa o estado do jogo
        with game_lock:
            game_state.clear()
            game_state.update({
                'active': False,
                'current_round': None,
                'player_name': 'TestPlayer',
                'player_uuid': None,
                'game_result': None,
                'thinking_uuid': None
            })

    def test_receive_round_result_with_dict_hand_info(self):
        """Testa receive_round_result_message com hand_info como dicionários."""
        winners = [
            {'uuid': 'player1', 'name': 'João'}
        ]
        hand_info = [
            {'uuid': 'player1', 'hand': 'PAIR', 'strength': 2}
        ]
        round_state = {
            'seats': [
                {'uuid': 'player1', 'name': 'João', 'stack': 120, 'state': 'participating', 'paid': 0}
            ],
            'pot': {'main': {'amount': 20}},
            'street': 'river',
            'community_card': ['SA', 'SK', 'SQ', 'SJ', 'ST'],
            'action_histories': {}
        }
        
        # Não deve lançar exceção
        try:
            self.player.receive_round_result_message(winners, hand_info, round_state)
            
            # Verifica que o estado foi atualizado corretamente
            with game_lock:
                self.assertIsNotNone(game_state.get('current_round'))
                self.assertTrue(game_state['current_round'].get('round_ended'))
                self.assertIsInstance(game_state['current_round'].get('hand_info'), list)
                self.assertIsInstance(game_state['current_round'].get('winners'), list)
                self.assertIsInstance(game_state['current_round'].get('final_stacks'), dict)
                
                # Verifica que hand_info foi serializado corretamente
                hand_info_result = game_state['current_round']['hand_info']
                self.assertEqual(len(hand_info_result), 1)
                self.assertEqual(hand_info_result[0]['uuid'], 'player1')
                
                # Verifica que winners foi serializado corretamente
                winners_result = game_state['current_round']['winners']
                self.assertEqual(len(winners_result), 1)
                self.assertEqual(winners_result[0]['uuid'], 'player1')
                
        except Exception as e:
            self.fail(f"receive_round_result_message lançou exceção: {e}")

    def test_receive_round_result_with_object_hand_info(self):
        """Testa receive_round_result_message com hand_info como objetos."""
        class MockHandInfo:
            def __init__(self, uuid, hand, strength):
                self.uuid = uuid
                self.hand = hand
                self.strength = strength
        
        winners = [
            {'uuid': 'player1', 'name': 'João'}
        ]
        hand_info = [
            MockHandInfo('player1', 'PAIR', 2)
        ]
        round_state = {
            'seats': [
                {'uuid': 'player1', 'name': 'João', 'stack': 120, 'state': 'participating', 'paid': 0}
            ],
            'pot': {'main': {'amount': 20}},
            'street': 'river',
            'community_card': [],
            'action_histories': {}
        }
        
        try:
            self.player.receive_round_result_message(winners, hand_info, round_state)
            
            with game_lock:
                hand_info_result = game_state['current_round']['hand_info']
                self.assertEqual(len(hand_info_result), 1)
                self.assertEqual(hand_info_result[0]['uuid'], 'player1')
                self.assertEqual(hand_info_result[0]['hand'], 'PAIR')
        except Exception as e:
            self.fail(f"receive_round_result_message lançou exceção: {e}")

    def test_receive_round_result_with_empty_data(self):
        """Testa receive_round_result_message com dados vazios."""
        winners = []
        hand_info = []
        round_state = {
            'seats': [],
            'pot': {'main': {'amount': 0}},
            'street': 'preflop',
            'community_card': [],
            'action_histories': {}
        }
        
        try:
            self.player.receive_round_result_message(winners, hand_info, round_state)
            
            with game_lock:
                self.assertIsNotNone(game_state.get('current_round'))
                self.assertEqual(game_state['current_round']['hand_info'], [])
                self.assertEqual(game_state['current_round']['winners'], [])
        except Exception as e:
            self.fail(f"receive_round_result_message lançou exceção com dados vazios: {e}")

    def test_receive_game_update_message(self):
        """Testa receive_game_update_message com diferentes formatos de action."""
        action = {
            'uuid': 'player1',
            'action': 'raise',
            'amount': 20
        }
        round_state = {
            'seats': [
                {'uuid': 'player1', 'name': 'João', 'stack': 100, 'state': 'participating', 'paid': 20}
            ],
            'pot': {'main': {'amount': 20}},
            'street': 'preflop',
            'community_card': [],
            'action_histories': {}
        }
        
        try:
            self.player.receive_game_update_message(action, round_state)
            
            with game_lock:
                self.assertIsNotNone(game_state.get('current_round'))
                self.assertIsNotNone(game_state['current_round'].get('action'))
                self.assertEqual(game_state['current_round']['action']['uuid'], 'player1')
                self.assertEqual(game_state['current_round']['action']['action'], 'raise')
        except Exception as e:
            self.fail(f"receive_game_update_message lançou exceção: {e}")

    def test_game_state_json_serializable(self):
        """Testa que game_state pode ser serializado para JSON."""
        # Preenche game_state com dados de teste
        with game_lock:
            game_state['current_round'] = {
                'round_count': 1,
                'round_ended': False,
                'round_state': {
                    'seats': [
                        {'uuid': 'p1', 'name': 'João', 'stack': 100, 'state': 'participating', 'paid': 10}
                    ],
                    'pot': {'main': {'amount': 20}},
                    'street': 'preflop',
                    'community_card': [],
                    'action_histories': {}
                },
                'hand_info': [
                    {'uuid': 'p1', 'hand': 'PAIR'}
                ],
                'winners': [
                    {'uuid': 'p1', 'name': 'João'}
                ],
                'final_stacks': {
                    'p1': {'name': 'João', 'stack': 120, 'won': True}
                }
            }
        
        # Tenta serializar para JSON
        try:
            json_str = json.dumps(game_state)
            self.assertIsInstance(json_str, str)
            
            # Tenta deserializar de volta
            parsed = json.loads(json_str)
            self.assertIsInstance(parsed, dict)
            self.assertIn('current_round', parsed)
        except (TypeError, ValueError) as e:
            self.fail(f"game_state não é serializável para JSON: {e}")

    def test_serialize_round_state_with_missing_seats(self):
        """Testa serialização quando seats está faltando."""
        round_state = {
            'pot': {'main': {'amount': 20}},
            'street': 'preflop'
        }
        
        result = self.player._serialize_round_state(round_state)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['seats'], [])
        self.assertEqual(result['pot']['main']['amount'], 20)

    def test_serialize_round_state_with_invalid_seats(self):
        """Testa serialização quando seats tem formato inválido."""
        round_state = {
            'seats': 'invalid',
            'pot': {'main': {'amount': 20}},
            'street': 'preflop'
        }
        
        # Não deve lançar exceção
        try:
            result = self.player._serialize_round_state(round_state)
            self.assertIsInstance(result, dict)
        except Exception as e:
            self.fail(f"_serialize_round_state lançou exceção: {e}")


if __name__ == '__main__':
    unittest.main()

