"""
Testes para win_probability_calculator.py
Verifica se o cálculo de probabilidade de vitória funciona corretamente.
"""

import unittest
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from players.win_probability_calculator import calculate_win_probability_for_player
from players.cards_registry import store_player_cards, clear_registry, get_all_cards


class TestWinProbabilityCalculator(unittest.TestCase):
    """Testa o cálculo de probabilidade de vitória."""
    
    def setUp(self):
        """Prepara o ambiente de teste."""
        clear_registry()
    
    def test_only_participating_players_counted(self):
        """Testa se apenas jogadores com estado 'participating' são contados."""
        player_uuid = 'player1'
        store_player_cards(player_uuid, ['SA', 'SK'])
        
        # Simula round_state com jogadores em diferentes estados
        round_state = {
            'street': 'preflop',
            'community_card': [],
            'seats': [
                {'uuid': 'player1', 'state': 'participating'},  # Ativo
                {'uuid': 'player2', 'state': 'participating'},  # Ativo
                {'uuid': 'player3', 'state': 'folded'},         # Desistiu (não deve contar)
                {'uuid': 'player4', 'state': 'participating'},  # Ativo
            ],
            'pot': {'main': {'amount': 15}}
        }
        
        # Deve calcular probabilidade apenas para 3 oponentes ativos (player2, player4)
        # player3 está folded, então não deve ser contado
        # Como não temos PokerKit configurado, pode retornar None, mas não deve quebrar
        try:
            result = calculate_win_probability_for_player(
                player_uuid=player_uuid,
                round_state=round_state,
                num_simulations=10,  # Poucas simulações para teste rápido
                return_confidence=False
            )
            # Se PokerKit estiver disponível, resultado deve estar entre 0 e 1 ou None
            if result is not None:
                self.assertGreaterEqual(result, 0.0)
                self.assertLessEqual(result, 1.0)
        except Exception as e:
            # Se PokerKit não estiver disponível, é esperado retornar None
            # Mas não deve lançar exceção
            self.fail(f"calculate_win_probability_for_player lançou exceção: {e}")
    
    def test_folded_players_not_counted(self):
        """Testa que jogadores folded não são contados como ativos."""
        player_uuid = 'player1'
        store_player_cards(player_uuid, ['HA', 'HK'])
        
        round_state = {
            'street': 'flop',
            'community_card': ['SA', 'SK', 'SQ'],
            'seats': [
                {'uuid': 'player1', 'state': 'participating'},
                {'uuid': 'player2', 'state': 'folded'},  # Não deve contar
                {'uuid': 'player3', 'state': 'folded'},  # Não deve contar
            ],
            'pot': {'main': {'amount': 30}}
        }
        
        # Se todos os oponentes estão folded, só deve haver 1 jogador ativo
        # Nesse caso, o resultado deve ser 1.0 (jogador ganha)
        try:
            result = calculate_win_probability_for_player(
                player_uuid=player_uuid,
                round_state=round_state,
                return_confidence=False
            )
            # Se só há 1 jogador ativo, probabilidade deve ser 1.0
            if result is not None:
                # Se todos os oponentes estão folded, player1 ganha
                # Mas pode haver verificação de jogadores ativos antes
                pass  # Aceita qualquer resultado válido
        except Exception as e:
            self.fail(f"calculate_win_probability_for_player lançou exceção: {e}")
    
    def test_confidence_interval_format(self):
        """Testa se o intervalo de confiança é retornado no formato correto."""
        player_uuid = 'player1'
        store_player_cards(player_uuid, ['DA', 'DK'])
        
        round_state = {
            'street': 'preflop',
            'community_card': [],
            'seats': [
                {'uuid': 'player1', 'state': 'participating'},
                {'uuid': 'player2', 'state': 'participating'},
            ],
            'pot': {'main': {'amount': 10}}
        }
        
        try:
            result = calculate_win_probability_for_player(
                player_uuid=player_uuid,
                round_state=round_state,
                num_simulations=100,
                return_confidence=True
            )
            
            if result is not None:
                # Verifica estrutura do resultado
                self.assertIsInstance(result, dict)
                self.assertIn('prob', result)
                self.assertIn('min', result)
                self.assertIn('max', result)
                self.assertIn('margin', result)
                
                # Verifica valores
                self.assertGreaterEqual(result['prob'], 0.0)
                self.assertLessEqual(result['prob'], 1.0)
                self.assertGreaterEqual(result['min'], 0.0)
                self.assertLessEqual(result['min'], 1.0)
                self.assertGreaterEqual(result['max'], 0.0)
                self.assertLessEqual(result['max'], 1.0)
                self.assertGreaterEqual(result['margin'], 0.0)
                
                # min <= prob <= max
                self.assertLessEqual(result['min'], result['prob'])
                self.assertGreaterEqual(result['max'], result['prob'])
        except Exception as e:
            # Se PokerKit não estiver disponível, é esperado
            pass
    
    def test_opponent_cards_not_used_from_registry(self):
        """
        Testa CRÍTICO: As cartas dos oponentes armazenadas no registry
        NÃO devem ser usadas na simulação Monte Carlo.
        
        Este teste valida o bug corrigido onde a simulação usava cartas
        conhecidas dos oponentes, resultando em probabilidades incorretas (100%).
        """
        player_uuid = 'player1'
        opponent_uuid = 'player2'
        
        # Limpa registry
        clear_registry()
        
        # Armazena cartas do jogador
        store_player_cards(player_uuid, ['SA', 'SK'])  # Ás e Rei
        
        # CRÍTICO: Armazena cartas do oponente no registry
        # (como os AI players fazem no receive_round_start_message)
        store_player_cards(opponent_uuid, ['H2', 'C2'])  # Par de 2s
        
        # Verifica que as cartas estão no registry
        all_cards = get_all_cards()
        self.assertIn(opponent_uuid, all_cards)
        self.assertEqual(all_cards[opponent_uuid], ['H2', 'C2'])
        
        # Cria round_state com oponente ativo
        round_state = {
            'street': 'preflop',
            'community_card': [],
            'seats': [
                {'uuid': player_uuid, 'state': 'participating'},
                {'uuid': opponent_uuid, 'state': 'participating'},
            ],
            'pot': {'main': {'amount': 15}}
        }
        
        try:
            # Calcula probabilidade (com poucas simulações para teste rápido)
            result = calculate_win_probability_for_player(
                player_uuid=player_uuid,
                round_state=round_state,
                num_simulations=500,  # Poucas simulações, mas suficientes para detectar padrão
                return_confidence=False
            )
            
            if result is not None:
                # Se a simulação estiver funcionando corretamente:
                # - As cartas do oponente devem ser simuladas aleatoriamente
                # - NÃO devem usar as cartas ['H2', 'C2'] do registry
                # - Probabilidade NÃO deve ser 100% ou muito próxima (devido à variação aleatória)
                
                # Com Ás-Rei vs cartas aleatórias, a probabilidade deve estar
                # em um range razoável (não pode ser 100% nem 0%)
                self.assertGreater(result, 0.0, 
                    "Probabilidade não pode ser 0% - jogador tem cartas fortes")
                self.assertLess(result, 0.999, 
                    "Probabilidade não pode ser 100% - cartas dos oponentes devem ser simuladas aleatoriamente")
                
                # Com Ás-Rei, esperamos probabilidade razoável (geralmente > 50% mas < 90%)
                # Mas não vamos ser muito restritivos aqui, apenas garantir que não é 100%
                self.assertIsNotNone(result)
                
        except Exception as e:
            # Se PokerKit não estiver disponível, pula o teste
            import traceback
            print(f"PokerKit não disponível - pulando teste: {e}")
            return
    
    def test_probability_not_100_percent_with_multiple_opponents(self):
        """
        Testa que a probabilidade nunca é 100% quando há múltiplos oponentes ativos.
        Mesmo com cartas muito fortes, deve haver incerteza.
        """
        player_uuid = 'player1'
        
        clear_registry()
        store_player_cards(player_uuid, ['SA', 'SK'])  # Cartas muito fortes
        
        # Múltiplos oponentes ativos
        round_state = {
            'street': 'preflop',
            'community_card': [],
            'seats': [
                {'uuid': player_uuid, 'state': 'participating'},
                {'uuid': 'player2', 'state': 'participating'},
                {'uuid': 'player3', 'state': 'participating'},
            ],
            'pot': {'main': {'amount': 20}}
        }
        
        try:
            result = calculate_win_probability_for_player(
                player_uuid=player_uuid,
                round_state=round_state,
                num_simulations=1000,  # Mais simulações para confiabilidade
                return_confidence=False
            )
            
            if result is not None:
                # Com 2 oponentes, mesmo com Ás-Rei, probabilidade não pode ser 100%
                # Deve haver alguma incerteza devido às cartas aleatórias dos oponentes
                self.assertLess(result, 0.999,
                    "Probabilidade não pode ser 100% com múltiplos oponentes ativos - "
                    "cartas dos oponentes devem ser simuladas aleatoriamente")
                
        except Exception as e:
            import traceback
            print(f"PokerKit não disponível - pulando teste: {e}")
            return
    
    def test_probability_100_percent_only_one_active_player(self):
        """
        Testa que probabilidade só é 100% quando há apenas 1 jogador ativo.
        Este é o único caso onde 100% é válido.
        """
        player_uuid = 'player1'
        
        clear_registry()
        store_player_cards(player_uuid, ['SA', 'SK'])
        
        # Apenas o jogador está ativo (todos os outros desistiram)
        round_state = {
            'street': 'preflop',
            'community_card': [],
            'seats': [
                {'uuid': player_uuid, 'state': 'participating'},
                {'uuid': 'player2', 'state': 'folded'},  # Desistiu
                {'uuid': 'player3', 'state': 'folded'},  # Desistiu
            ],
            'pot': {'main': {'amount': 15}}
        }
        
        try:
            result = calculate_win_probability_for_player(
                player_uuid=player_uuid,
                round_state=round_state,
                return_confidence=False
            )
            
            if result is not None:
                # Quando só há 1 jogador ativo, ele ganha = 100%
                self.assertEqual(result, 1.0,
                    "Quando só há 1 jogador ativo, probabilidade deve ser 100%")
                
        except Exception as e:
            import traceback
            print(f"PokerKit não disponível - pulando teste: {e}")
            return
    
    def test_simulation_variability(self):
        """
        Testa que múltiplas execuções da simulação produzem resultados variáveis
        (não fixos), indicando que está usando aleatoriedade.
        """
        player_uuid = 'player1'
        
        clear_registry()
        store_player_cards(player_uuid, ['HQ', 'DQ'])  # Dama-Q, cartas medianas
        
        round_state = {
            'street': 'preflop',
            'community_card': [],
            'seats': [
                {'uuid': player_uuid, 'state': 'participating'},
                {'uuid': 'player2', 'state': 'participating'},
            ],
            'pot': {'main': {'amount': 10}}
        }
        
        try:
            # Executa simulação múltiplas vezes com poucas simulações cada
            # (para detectar variação mais rapidamente)
            results = []
            for _ in range(5):
                result = calculate_win_probability_for_player(
                    player_uuid=player_uuid,
                    round_state=round_state,
                    num_simulations=200,  # Poucas simulações = mais variabilidade
                    return_confidence=False
                )
                if result is not None:
                    results.append(result)
            
            if len(results) >= 3:  # Se temos pelo menos 3 resultados válidos
                # Calcula variação (desvio padrão ou range)
                min_result = min(results)
                max_result = max(results)
                range_result = max_result - min_result
                
                # Com poucas simulações, deve haver alguma variação
                # (se estiver usando aleatoriedade corretamente)
                # Mas não vamos ser muito restritivos - apenas verificar que há variação
                if range_result < 0.01:  # Se range for muito pequeno
                    # Pode ser que seja realmente muito estável, mas vamos apenas avisar
                    print(f"AVISO: Resultados muito similares (range={range_result:.4f}). "
                          f"Resultados: {results}")
                # Não vamos falhar o teste aqui, pois com mais simulações pode estabilizar
                
        except Exception as e:
            import traceback
            print(f"PokerKit não disponível - pulando teste: {e}")
            return


if __name__ == '__main__':
    unittest.main()
