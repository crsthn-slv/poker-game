"""
Testes unitários para serialização de hand_info e winners.
Testa diferentes formatos de dados que podem ser retornados pelo PyPokerEngine.
"""

import sys
import os
import unittest

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.server import WebPlayer


class TestSerialization(unittest.TestCase):
    """Testa funções de serialização do WebPlayer."""

    def setUp(self):
        """Prepara o ambiente de teste."""
        self.player = WebPlayer()

    def test_serialize_hand_info_with_dicts(self):
        """Testa serialização de hand_info quando contém dicionários."""
        hand_info = [
            {'uuid': 'player1', 'hand': 'PAIR', 'strength': 2},
            {'uuid': 'player2', 'hand': 'HIGH_CARD', 'strength': 1}
        ]
        result = self.player._serialize_hand_info(hand_info)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['uuid'], 'player1')
        self.assertEqual(result[1]['hand'], 'HIGH_CARD')

    def test_serialize_hand_info_with_objects(self):
        """Testa serialização de hand_info quando contém objetos."""
        class MockHandInfo:
            def __init__(self, uuid, hand, strength):
                self.uuid = uuid
                self.hand = hand
                self.strength = strength
        
        hand_info = [
            MockHandInfo('player1', 'PAIR', 2),
            MockHandInfo('player2', 'HIGH_CARD', 1)
        ]
        result = self.player._serialize_hand_info(hand_info)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['uuid'], 'player1')
        self.assertEqual(result[1]['hand'], 'HIGH_CARD')

    def test_serialize_hand_info_mixed(self):
        """Testa serialização de hand_info com tipos mistos."""
        class MockHandInfo:
            def __init__(self, uuid):
                self.uuid = uuid
        
        hand_info = [
            {'uuid': 'player1', 'hand': 'PAIR'},
            MockHandInfo('player2')
        ]
        result = self.player._serialize_hand_info(hand_info)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['uuid'], 'player1')
        self.assertEqual(result[1]['uuid'], 'player2')

    def test_serialize_hand_info_empty(self):
        """Testa serialização de hand_info vazio."""
        result = self.player._serialize_hand_info([])
        self.assertEqual(result, [])
        
        result = self.player._serialize_hand_info(None)
        self.assertEqual(result, [])

    def test_serialize_winners_with_dicts(self):
        """Testa serialização de winners quando contém dicionários."""
        winners = [
            {'uuid': 'player1', 'name': 'João'},
            {'uuid': 'player2', 'name': 'Maria'}
        ]
        result = self.player._serialize_winners(winners)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['uuid'], 'player1')
        self.assertEqual(result[1]['name'], 'Maria')

    def test_serialize_winners_with_objects(self):
        """Testa serialização de winners quando contém objetos."""
        class MockWinner:
            def __init__(self, uuid, name):
                self.uuid = uuid
                self.name = name
        
        winners = [
            MockWinner('player1', 'João'),
            MockWinner('player2', 'Maria')
        ]
        result = self.player._serialize_winners(winners)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['uuid'], 'player1')
        self.assertEqual(result[1]['name'], 'Maria')

    def test_serialize_winners_empty(self):
        """Testa serialização de winners vazio."""
        result = self.player._serialize_winners([])
        self.assertEqual(result, [])
        
        result = self.player._serialize_winners(None)
        self.assertEqual(result, [])

    def test_serialize_winners_with_attributes(self):
        """Testa serialização de winners com objetos que têm apenas atributos."""
        class MockWinner:
            def __init__(self, uuid):
                self.uuid = uuid
                self.name = 'Test'
        
        winners = [MockWinner('player1')]
        result = self.player._serialize_winners(winners)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['uuid'], 'player1')
        self.assertEqual(result[0]['name'], 'Test')

    def test_serialize_round_state_basic(self):
        """Testa serialização básica de round_state."""
        round_state = {
            'seats': [
                {'uuid': 'p1', 'name': 'João', 'stack': 100, 'state': 'participating', 'paid': 10},
                {'uuid': 'p2', 'name': 'Maria', 'stack': 90, 'state': 'folded', 'paid': 0}
            ],
            'pot': {'main': {'amount': 20}},
            'street': 'preflop',
            'community_card': [],
            'action_histories': {}
        }
        
        result = self.player._serialize_round_state(round_state)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result['seats']), 2)
        self.assertEqual(result['pot']['main']['amount'], 20)
        self.assertEqual(result['street'], 'preflop')

    def test_serialize_round_state_with_missing_fields(self):
        """Testa serialização de round_state com campos faltando."""
        round_state = {
            'seats': []
        }
        
        result = self.player._serialize_round_state(round_state)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['seats'], [])
        self.assertIn('pot', result)
        self.assertIn('street', result)

    def test_serialize_round_state_empty(self):
        """Testa serialização de round_state vazio."""
        round_state = {}
        result = self.player._serialize_round_state(round_state)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['seats'], [])
        self.assertEqual(result['street'], 'preflop')


if __name__ == '__main__':
    unittest.main()

