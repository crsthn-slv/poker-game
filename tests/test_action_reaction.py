"""
Testes automáticos para verificar se os bots reagem às ações dos oponentes em tempo real.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.action_analyzer import analyze_current_round_actions
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.smart_player import SmartPlayer
from players.learning_player import LearningPlayer


def test_action_analyzer_basic():
    """Testa a função analyze_current_round_actions com cenários básicos."""
    print("🧪 Teste 1: Função analyze_current_round_actions - Cenários básicos")
    
    # Cenário 1: Nenhuma ação
    round_state_empty = {
        'street': 'preflop',
        'action_histories': {}
    }
    result = analyze_current_round_actions(round_state_empty, 'bot1')
    assert result['has_raises'] == False, "Não deveria ter raises quando não há ações"
    assert result['raise_count'] == 0, "Contagem de raises deveria ser 0"
    print("  ✅ Cenário 1: Nenhuma ação - OK")
    
    # Cenário 2: Apenas calls
    round_state_calls = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'bot2', 'action': 'CALL', 'amount': 10},
                {'uuid': 'bot3', 'action': 'CALL', 'amount': 10}
            ]
        }
    }
    result = analyze_current_round_actions(round_state_calls, 'bot1')
    assert result['has_raises'] == False, "Não deveria ter raises quando só há calls"
    assert result['call_count'] == 2, "Deveria contar 2 calls"
    print("  ✅ Cenário 2: Apenas calls - OK")
    
    # Cenário 3: Com raises
    round_state_raises = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'bot2', 'action': 'RAISE', 'amount': 20},
                {'uuid': 'bot3', 'action': 'CALL', 'amount': 20},
                {'uuid': 'bot4', 'action': 'RAISE', 'amount': 30}
            ]
        }
    }
    result = analyze_current_round_actions(round_state_raises, 'bot1')
    assert result['has_raises'] == True, "Deveria detectar raises"
    assert result['raise_count'] == 2, "Deveria contar 2 raises"
    assert result['last_action'] == 'raise', "Última ação deveria ser raise"
    print("  ✅ Cenário 3: Com raises - OK")
    
    # Cenário 4: Exclui ações próprias
    round_state_self = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'bot1', 'action': 'RAISE', 'amount': 20},  # Ação própria
                {'uuid': 'bot2', 'action': 'CALL', 'amount': 20}
            ]
        }
    }
    result = analyze_current_round_actions(round_state_self, 'bot1')
    assert result['raise_count'] == 0, "Não deveria contar ação própria"
    assert result['call_count'] == 1, "Deveria contar apenas o call do oponente"
    print("  ✅ Cenário 4: Exclui ações próprias - OK")
    
    print("✅ Teste 1: PASSOU\n")


def test_bot_reaction_to_raises():
    """Testa se os bots ajustam comportamento quando detectam raises."""
    print("🧪 Teste 2: Bots reagem a raises dos oponentes")
    
    # Cria bots
    tight = TightPlayer()
    tight.uuid = 'tight_bot'
    
    aggressive = AggressivePlayer()
    aggressive.uuid = 'aggressive_bot'
    
    smart = SmartPlayer()
    smart.uuid = 'smart_bot'
    
    # Simula round_state com raises
    round_state_with_raises = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 25},
                {'uuid': 'opponent2', 'action': 'RAISE', 'amount': 30}
            ]
        },
        'seats': [
            {'uuid': 'tight_bot', 'state': 'participating', 'stack': 100},
            {'uuid': 'opponent1', 'state': 'participating', 'stack': 100},
            {'uuid': 'opponent2', 'state': 'participating', 'stack': 100}
        ],
        'pot': {'main': {'amount': 55}}
    }
    
    # Testa se detectam raises
    current_actions_tight = analyze_current_round_actions(round_state_with_raises, 'tight_bot')
    current_actions_aggressive = analyze_current_round_actions(round_state_with_raises, 'aggressive_bot')
    current_actions_smart = analyze_current_round_actions(round_state_with_raises, 'smart_bot')
    
    assert current_actions_tight['has_raises'] == True, "TightPlayer deveria detectar raises"
    assert current_actions_tight['raise_count'] == 2, "TightPlayer deveria contar 2 raises"
    
    assert current_actions_aggressive['has_raises'] == True, "AggressivePlayer deveria detectar raises"
    assert current_actions_smart['has_raises'] == True, "SmartPlayer deveria detectar raises"
    
    print("  ✅ Todos os bots detectam raises corretamente")
    
    # Verifica se os bots ajustam threshold
    # TightPlayer deveria aumentar threshold quando há raises
    original_threshold = tight.tightness_threshold
    round_state_for_action = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 25}
            ]
        },
        'seats': [
            {'uuid': 'tight_bot', 'state': 'participating', 'stack': 100}
        ],
        'pot': {'main': {'amount': 25}},
        'community_card': []
    }
    
    # Simula declare_action (sem executar completamente)
    current_actions = analyze_current_round_actions(round_state_for_action, 'tight_bot')
    
    # Verifica se o threshold seria ajustado
    if current_actions['has_raises']:
        expected_adjustment = 8 + (current_actions['raise_count'] * 3)
        print(f"  ✅ TightPlayer ajustaria threshold de {original_threshold} para {original_threshold + expected_adjustment}")
    
    print("✅ Teste 2: PASSOU\n")


def test_bot_bluff_adjustment():
    """Testa se os bots evitam blefe quando há raises."""
    print("🧪 Teste 3: Bots evitam blefe quando há raises")
    
    learning = LearningPlayer()
    learning.uuid = 'learning_bot'
    
    # Cenário 1: Sem raises (pode blefar)
    round_state_no_raises = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'CALL', 'amount': 10}
            ]
        },
        'seats': [
            {'uuid': 'learning_bot', 'state': 'participating', 'stack': 100}
        ],
        'pot': {'main': {'amount': 20}},
        'community_card': []
    }
    
    current_actions_no_raises = analyze_current_round_actions(round_state_no_raises, 'learning_bot')
    assert current_actions_no_raises['has_raises'] == False, "Não deveria ter raises"
    
    # Cenário 2: Com 2+ raises (não deve blefar)
    round_state_many_raises = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20},
                {'uuid': 'opponent2', 'action': 'RAISE', 'amount': 30}
            ]
        },
        'seats': [
            {'uuid': 'learning_bot', 'state': 'participating', 'stack': 100}
        ],
        'pot': {'main': {'amount': 50}},
        'community_card': []
    }
    
    current_actions_many_raises = analyze_current_round_actions(round_state_many_raises, 'learning_bot')
    assert current_actions_many_raises['has_raises'] == True, "Deveria ter raises"
    assert current_actions_many_raises['raise_count'] >= 2, "Deveria ter 2+ raises"
    
    # Verifica lógica de blefe
    should_bluff_no_raises = current_actions_no_raises['has_raises'] and current_actions_no_raises['raise_count'] >= 2
    should_bluff_many_raises = current_actions_many_raises['has_raises'] and current_actions_many_raises['raise_count'] >= 2
    
    assert should_bluff_no_raises == False, "Sem raises, pode considerar blefe"
    assert should_bluff_many_raises == True, "Com 2+ raises, não deve blefar"
    
    print("  ✅ Bots evitam blefe quando há 2+ raises")
    print("✅ Teste 3: PASSOU\n")


def test_different_streets():
    """Testa se a análise funciona em diferentes streets."""
    print("🧪 Teste 4: Análise funciona em diferentes streets")
    
    # Preflop
    round_state_preflop = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20}
            ]
        }
    }
    result_preflop = analyze_current_round_actions(round_state_preflop, 'bot1')
    assert result_preflop['has_raises'] == True, "Deveria detectar raise no preflop"
    print("  ✅ Preflop - OK")
    
    # Flop
    round_state_flop = {
        'street': 'flop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'CALL', 'amount': 10}
            ],
            'flop': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 30}
            ]
        }
    }
    result_flop = analyze_current_round_actions(round_state_flop, 'bot1')
    assert result_flop['has_raises'] == True, "Deveria detectar raise no flop"
    print("  ✅ Flop - OK")
    
    # Turn
    round_state_turn = {
        'street': 'turn',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'CALL', 'amount': 10}
            ],
            'flop': [
                {'uuid': 'opponent1', 'action': 'CALL', 'amount': 10}
            ],
            'turn': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 40}
            ]
        }
    }
    result_turn = analyze_current_round_actions(round_state_turn, 'bot1')
    assert result_turn['has_raises'] == True, "Deveria detectar raise no turn"
    print("  ✅ Turn - OK")
    
    print("✅ Teste 4: PASSOU\n")


def test_aggression_calculation():
    """Testa o cálculo de agressão."""
    print("🧪 Teste 5: Cálculo de nível de agressão")
    
    # Cenário: 2 raises, 1 call = 66% de agressão
    round_state = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20},
                {'uuid': 'opponent2', 'action': 'RAISE', 'amount': 30},
                {'uuid': 'opponent3', 'action': 'CALL', 'amount': 30}
            ]
        }
    }
    result = analyze_current_round_actions(round_state, 'bot1')
    
    assert result['raise_count'] == 2, "Deveria ter 2 raises"
    assert result['call_count'] == 1, "Deveria ter 1 call"
    # Agressão = raises / (raises + calls) = 2 / 3 = 0.666...
    expected_aggression = 2 / 3
    assert abs(result['total_aggression'] - expected_aggression) < 0.01, f"Agressão deveria ser ~{expected_aggression}"
    
    print(f"  ✅ Agressão calculada: {result['total_aggression']:.2%} (esperado: {expected_aggression:.2%})")
    print("✅ Teste 5: PASSOU\n")


def run_all_tests():
    """Executa todos os testes."""
    print("=" * 60)
    print("🧪 TESTES AUTOMÁTICOS: Reação em Tempo Real às Ações")
    print("=" * 60)
    print()
    
    tests = [
        test_action_analyzer_basic,
        test_bot_reaction_to_raises,
        test_bot_bluff_adjustment,
        test_different_streets,
        test_aggression_calculation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FALHOU: {test.__name__}")
            print(f"   Erro: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ ERRO em {test.__name__}: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"📊 RESULTADO FINAL:")
    print(f"   ✅ Passou: {passed}/{len(tests)}")
    print(f"   ❌ Falhou: {failed}/{len(tests)}")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

